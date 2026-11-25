/**
 * RAM measurement of a PySwitch firmware on an emulated RP2040 (rp2040js), used by ../../build (runs in the runner
 * container). Derived from the RAM tool of claude/002 (tools/rp2040_ram/measure.mts).
 *
 * The firmware must be a debug build (memory monitoring of PySwitch switched on and the RAM probe imported in the frozen
 * pyswitch/process.py, see prepare_frozen.py); the drive folder must contain _ramprobe.py (ramprobe.py).
 *
 * Usage: tsx --tsconfig /opt/rp2040js/tsconfig.json measure.mts --drive=<folder> --uf2=<file> [--seconds=<n>] [--timeout=<n>]
 *     --seconds   emulated run time after loading, for the minimum free RAM (default 10)
 *     --timeout   real time limit in seconds (default 900)
 *
 * Prints the report and one line "RESULT_JSON {...}".
 */

import { execFileSync } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

import { Simulator } from '/opt/rp2040js/src/simulator.js';
import { USBCDC } from '/opt/rp2040js/src/usb/cdc.js';
import { ConsoleLogger, LogLevel } from '/opt/rp2040js/src/utils/logging.js';
import { bootromB1 } from '/opt/rp2040js/demo/bootrom.js';
import { loadCircuitpythonFlashImage, loadUF2 } from '/opt/rp2040js/demo/load-flash.js';

// Size of the CIRCUITPY drive in kB (the MIDI Captain has more than 7 MB; claude/002 SPEC 2.1)
const DRIVE_SIZE_KB = 10240;

// Number of console lines shown when the measurement fails
const NUM_ERROR_LINES = 40;

/**
 * Parses the command line arguments.
 */
function parseArguments() {
    const ret = { drive: '', uf2: '', seconds: 10, timeout: 900 };
    for (const arg of process.argv.slice(2)) {
        const [key, value] = arg.split('=');
        if (key == '--drive') ret.drive = value;
        else if (key == '--uf2') ret.uf2 = value;
        else if (key == '--seconds') ret.seconds = parseInt(value);
        else if (key == '--timeout') ret.timeout = parseInt(value);
        else throw new Error('Unknown option: ' + arg);
    }
    if (!ret.drive || !ret.uf2) throw new Error('--drive and --uf2 are needed');
    return ret;
}

/**
 * Creates the FAT image of the CIRCUITPY drive from a folder. Returns its path.
 */
function createImage(driveFolder: string, workFolder: string) {
    const image = path.join(workFolder, 'drive.img');
    execFileSync('mkfs.fat', ['-C', '-F', '16', '-S', '512', '-r', '64', '-n', 'CIRCUITPY', image, String(DRIVE_SIZE_KB)], { stdio: 'ignore' });
    const entries = fs.readdirSync(driveFolder).map((entry) => path.join(driveFolder, entry));
    execFileSync('mcopy', ['-s', '-i', image, ...entries, '::/'], { env: { ...process.env, MTOOLS_SKIP_CHECK: '1' }, stdio: ['ignore', 'ignore', 'inherit'] });
    return image;
}

/**
 * Runs the measurement.
 */
function main() {
    const args = parseArguments();
    const work = fs.mkdtempSync(path.join(os.tmpdir(), 'measure-'));
    const image = createImage(args.drive, work);

    const simulator = new Simulator();
    const mcu = simulator.rp2040;
    mcu.loadBootrom(bootromB1);
    mcu.logger = new ConsoleLogger(LogLevel.Error);
    loadUF2(args.uf2, mcu);
    loadCircuitpythonFlashImage(image, mcu);

    // All inputs idle high: switches not pressed (also the USB drive switch in boot.py), UART RX idle
    for (const pin of mcu.gpio) {
        pin.setInputValue(true);
    }

    // SPI (display): complete every byte after its real transfer time (with immediate completion, CircuitPython's
    // DMA transfers lose bytes and hang; claude/002 SPEC 2.2)
    for (const spi of mcu.spi) {
        const alarm = simulator.clock.createAlarm(() => spi.completeTransmit(0));
        spi.onTransmit = () => {
            const frequency = spi.clockFrequency;
            alarm.schedule(frequency > 0 ? spi.dataBits * 1e9 / frequency : 1000);
        };
    }

    const result = { status: '', startFree: -1, total: -1, showingUi: -1, loadedFree: -1, minFree: -1, block: -1, loadedNanos: -1, realSeconds: 0, emulatedSeconds: 0 };
    const lastLines: string[] = [];
    const startTime = Date.now();
    let memoryError = false;

    /**
     * Prints the report and exits.
     */
    function finish(status: string, exitCode: number) {
        simulator.stop();
        result.status = status;
        result.realSeconds = (Date.now() - startTime) / 1000;
        result.emulatedSeconds = simulator.clock.nanos / 1e9;

        const kib = (bytes: number) => bytes + ' B (' + (bytes / 1024).toFixed(1) + ' KiB)';
        console.log('Heap:                   ' + kib(result.total));
        console.log('Free at start:          ' + kib(result.startFree));
        console.log('Free at "Showing UI":   ' + kib(result.showingUi));
        console.log('Free after loading:     ' + kib(result.loadedFree));
        console.log('Largest free block:     ' + kib(result.block));
        console.log(('Minimum free (' + args.seconds + ' s):').padEnd(24) + kib(result.minFree));
        console.log('Result:                 ' + status);
        if (exitCode != 0) {
            console.log('Last console lines:');
            for (const line of lastLines) console.log('    ' + line);
        }
        console.log('RESULT_JSON ' + JSON.stringify(result));

        fs.rmSync(work, { recursive: true, force: true });
        process.exit(exitCode);
    }

    /**
     * Handles one line of the serial console (lines of the RAM probe, see ramprobe.py).
     */
    function processLine(line: string) {
        lastLines.push(line);
        if (lastLines.length > NUM_ERROR_LINES) lastLines.shift();

        if (line.includes('MemoryError')) memoryError = true;
        if (line.includes('Code done running')) finish(memoryError ? 'MEMORY ERROR' : 'PROGRAM ENDED (error)', 1);

        const probe = line.match(/^RAMPROBE (\w+) (.*)$/);
        if (!probe) return;
        const values = probe[2].split(' ');
        if (probe[1] == 'start') {
            result.startFree = parseInt(values[0]);
            result.total = parseInt(values[1]);
        } else if (probe[1] == 'free') {
            const free = parseInt(values[0]);
            const prefix = values.slice(1).join(' ');
            if (prefix == 'Showing UI') {
                result.showingUi = free;
            } else if (prefix == 'Application loaded') {
                result.loadedFree = free;
                result.minFree = free;
                result.loadedNanos = simulator.clock.nanos;
            } else if (result.loadedNanos >= 0 && free < result.minFree) {
                result.minFree = free;
            }
        } else if (probe[1] == 'block') {
            result.block = parseInt(values[0]);
        }
    }

    // End of the run time (emulated) after loading
    setInterval(() => {
        if (result.loadedNanos >= 0 && result.block >= 0 && simulator.clock.nanos - result.loadedNanos >= args.seconds * 1e9) {
            finish('OK', 0);
        }
    }, 100);

    setTimeout(() => finish(memoryError ? 'MEMORY ERROR' : 'TIMEOUT (' + args.timeout + ' s real time)', 2), args.timeout * 1000);

    // Serial console (USB CDC)
    const cdc = new USBCDC(mcu.usbCtrl);
    let currentLine = '';
    cdc.onSerialData = (value: Uint8Array) => {
        for (const byte of value) {
            const char = String.fromCharCode(byte);
            if (char == '\n') {
                processLine(currentLine.replace(/\r/g, ''));
                currentLine = '';
            } else {
                currentLine += char;
            }
        }
    };

    mcu.core.PC = 0x10000000;
    simulator.execute();
}

try {
    main();
} catch (e: any) {
    console.error('Error: ' + (e.message ?? e));
    process.exit(3);
}
