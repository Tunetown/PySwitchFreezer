# PySwitch build: optimized UF2

Builds an optimized UF2 image from PySwitch: one command fetches a branch of [PySwitch](https://github.com/Tunetown/PySwitch) from GitHub, runs its unit tests, builds a CircuitPython 7.3.1 firmware with PySwitch and its libraries already inside, and collects everything you need to copy onto the device. It also measures how much RAM is left on an emulated device and writes a report.

**Why**: normally CircuitPython compiles PySwitch on the device at every start and keeps the compiled program in RAM. In this firmware, PySwitch and its libraries are precompiled and stored in the flash memory of the chip, so most of the RAM stays free for your configuration (default configuration of `main`: about 132 KiB free after loading instead of about 53 KiB).

**Contents**

1. [Quick start](#1-quick-start)
2. [Requirements](#2-requirements)
3. [Usage](#3-usage)
4. [Output](#4-output)
5. [Installing on the device](#5-installing-on-the-device)
6. [What the build does](#6-what-the-build-does)
7. [Frozen modules](#7-frozen-modules)
8. [The report and the RAM measurement](#8-the-report-and-the-ram-measurement)
9. [Developing PySwitch with this firmware](#9-developing-pyswitch-with-this-firmware)
10. [Tests of the build program](#10-tests-of-the-build-program)
11. [Project layout and configuration](#11-project-layout-and-configuration)
12. [Troubleshooting](#12-troubleshooting)
13. [Cleaning up](#13-cleaning-up)
14. [Limitations](#14-limitations)


## 1. Quick start

    ./build

Builds the branch `main`. The first run takes about 30 minutes (the Docker image with CircuitPython, the compiler and the emulator is built once); every later run takes about 2 minutes. When it is done:

1. Copy `output/PySwitch.uf2` to the device in bootloader mode (drive `RPI-RP2`).
2. Copy the contents of `output/drive/` to the `CIRCUITPY` drive.

`output/REPORT.md` shows what was built.


## 2. Requirements

| Needed           | Remark                                                                                      |
|------------------|---------------------------------------------------------------------------------------------|
| Linux or macOS   | with `bash` (on Windows: WSL)                                                               |
| Docker           | with Docker Compose (`docker compose`); everything else runs inside the container           |
| Internet access  | the build fetches PySwitch and the library sources from GitHub                              |
| Disk space       | about 4 GB for the Docker image                                                             |

Works on x86_64 and ARM64 (aarch64) machines. `git`, Python and the compilers are **not** needed on your machine.


## 3. Usage

    ./build [<branch>] [options]

| Argument / option   | Meaning                                                                                       |
|---------------------|-----------------------------------------------------------------------------------------------|
| `<branch>`          | branch or tag of PySwitch to build (default: `main`)                                          |
| `--example <path>`  | measure the RAM with an example configuration instead of the default one (path relative to `examples/` of PySwitch); the drive files in the output keep the default configuration |
| `--force`           | replace the sources folder even if it was not created by the build (section 12)               |
| `--sources <folder>`| use another sources folder (default `pyswitch/`; must be inside this project folder)          |
| `--output <folder>` | use another output folder (default `output/`; must be inside this project folder)             |
| `--help`            | show the options                                                                              |

Examples:

    ./build                                            # main
    ./build dev_midi                                   # another branch
    ./build v2.4.10                                    # a tag
    ./build main --example "Kemper Profiler/MIDICaptain 10/Expression Pedals and Wheel"

The build stops with an error message (and builds nothing) if the branch does not exist or the unit tests of the branch fail.


## 4. Output

Everything is written to `output/` (deleted and created again on every run):

| File / folder   | Content                                                                                       |
|-----------------|-----------------------------------------------------------------------------------------------|
| `PySwitch.uf2`  | the firmware: CircuitPython 7.3.1 with PySwitch and its libraries built in                    |
| `drive/`        | the files for the `CIRCUITPY` drive (section 5)                                                |
| `REPORT.md`     | sources (branch, commit), unit tests, flash use, frozen modules with versions, drive files, RAM measurement |
| `logs/`         | details: `tests.txt` (unit test output), `build_release.log` / `build_debug.log` (firmware builds), `frozen_modules.json` (every frozen module with its source), `measurement.txt` (RAM measurement) |

The PySwitch sources of the build are in `pyswitch/` (a shallow clone of the branch; replaced on the next run).


## 5. Installing on the device

1. **Firmware**: put the device into bootloader mode (a drive `RPI-RP2` appears; on most RP2040 boards: hold the BOOT button while connecting USB) and copy `PySwitch.uf2` onto it. The device restarts with the new firmware. This works like installing the official CircuitPython UF2; you can always go back by copying the official UF2.
2. **Drive files**: copy the contents of `output/drive/` to the `CIRCUITPY` drive: `boot.py`, `code.py`, the configuration files (`config.py`, `inputs.py`, `display.py`, `communication.py`), `fonts/` and the libraries that are not built in.
3. **Your configuration**: replace the configuration files by your own, as before. Configurations stay on the drive and can be edited and transferred as always (for example with the PySwitch emulator or the MIDI bridge).

The drive does **not** need `lib/pyswitch` or the built-in libraries; if they are there, they are ignored (section 7).


## 6. What the build does

| Step | What happens                                                                                     |
|------|--------------------------------------------------------------------------------------------------|
| 1    | **Fetch** the branch from GitHub into `pyswitch/`                                                |
| 2    | **Unit tests** of PySwitch (with coverage); if they fail, the build stops                        |
| 3    | **Firmware**: PySwitch and the libraries it imports are compiled into CircuitPython 7.3.1 → `PySwitch.uf2`; a second, debug firmware with PySwitch's memory monitoring switched on is built for the measurement (not in the output) |
| 4    | **Drive files**: the `content/` folder of PySwitch without the built-in modules → `drive/`        |
| 5    | **RAM measurement**: the debug firmware and the drive files run on an emulated RP2040            |
| 6    | **Report**: `REPORT.md`                                                                           |

**CircuitPython itself is not changed.** Building Python modules into the firmware ("freezing") is a standard feature of the CircuitPython build, also used by official boards for their libraries. The firmware is a complete CircuitPython 7.3.1; PySwitch and its libraries are additions.


## 7. Frozen modules

**Which**: PySwitch itself and every library of PySwitch's `content/lib` that PySwitch imports, in its core or in any of its actions (for example `adafruit_display_text`, `adafruit_bitmap_font`, `adafruit_hid`, NeoPixel, ST7789, PyMidiBridge). Libraries that PySwitch does not import stay on the drive. The exact list of a build is in `REPORT.md`.

**Versions**: the build uses exactly the library versions of the branch: it reads the version and the repository of each library from its `.mpy` files in `content/lib` and builds the library from its source code at that version. If a version tag does not exist, the default branch of the library is used, and the report says so.

**Search order**: CircuitPython looks for a module first in the root folder of the drive, then in the firmware, then in `lib/`. Consequences:

- A `lib/pyswitch` (or a built-in library) on the drive is **ignored**: the firmware version is used.
- A **newer PySwitch or library version needs a new firmware** (run the build again).
- A `pyswitch` folder in the **root folder** of the drive overrides the built-in PySwitch (section 9).


## 8. The report and the RAM measurement

The RAM is measured on an **emulated RP2040** (the [rp2040js](https://github.com/wokwi/rp2040js) emulator running the real CircuitPython firmware): the same firmware, the same bytecode and the same memory management as on the device, so the values after loading match the device exactly. The measurement runs the debug firmware (identical to `PySwitch.uf2`, plus PySwitch's memory monitoring) with the drive files, without a connected MIDI device, for 10 seconds of emulated time after loading.

| Value in the report          | Meaning                                                                         |
|------------------------------|---------------------------------------------------------------------------------|
| Heap                         | total memory for Python objects                                                 |
| Free at start                | free memory when PySwitch starts                                                |
| Free at "Showing UI"         | free memory after the configuration has been loaded, before the display is set up |
| **Free after loading**       | free memory when PySwitch is ready: the main value                              |
| Largest free block           | largest piece of memory that can be allocated at once (fragmentation)           |
| Minimum free during the run  | lowest free memory during the 10 s run                                          |

The measured configuration is the default configuration of `content/`, or the example given with `--example`. With a connected device (rig names, MIDI traffic) PySwitch needs some more memory at runtime than in the measurement.

The measurement needs the two commented memory monitoring lines in PySwitch's `lib/pyswitch/process.py`; if a branch does not have them, the build skips the measurement and says so.


## 9. Developing PySwitch with this firmware

1. Change the Python code of PySwitch as usual (unit tests and the web emulator work on the `.py` files as before).
2. Push the branch and run `./build <branch>`.
3. Install the output (section 5).

To **try a change on the device without a new firmware**, copy PySwitch's `content/lib/pyswitch` to the **root folder** of the drive (`/pyswitch`, not `/lib/pyswitch`): it overrides the built-in version. This needs as much RAM as PySwitch without this firmware, so large configurations may not fit. Delete `/pyswitch` afterwards.


## 10. Tests of the build program

    ./test            # unit tests of the build program
    ./test -v         # with the name of every test

Runs the unit tests of the build program (`docker/tests`) in the build container. They replace `git`, the CircuitPython build and the emulator by mocks, so they need no network and take about a second. The results are shown in the terminal. (The unit tests of **PySwitch** are run by `./build`, see `output/logs/tests.txt`.)


## 11. Project layout and configuration

| Path                  | Content                                                                    |
|-----------------------|----------------------------------------------------------------------------|
| `build`               | the command (starts the build program in its container)                    |
| `test`                | runs the tests of the build program                                         |
| `docker/Dockerfile`   | the Docker image: CircuitPython 7.3.1 sources, ARM compiler, Python, Node with rp2040js |
| `docker/compose.yaml` | the container (mounts this folder at `/work`)                              |
| `docker/builder/`     | the build program (Python), one module per step                            |
| `docker/tests/`       | tests of the build program                                                 |
| `docker/scripts/`     | RAM measurement (`measure.mts`) and the memory probe used by it            |
| `pyswitch/`           | PySwitch sources of the last build (not versioned)                         |
| `output/`             | output of the last build (not versioned)                                   |

**Configuration**: all settings are constants in `docker/builder/constants.py`: the PySwitch repository URL, the default branch, the folders, the output names, repositories of libraries whose `.mpy` files contain no repository URL, and the duration of the RAM measurement.


## 12. Troubleshooting

| Message / problem                                             | Cause and solution                                                              |
|---------------------------------------------------------------|---------------------------------------------------------------------------------|
| `pyswitch exists and was not created by the build`            | the sources folder contains files the build did not create (for example your own work); the build does not delete them. Move them away, or use `--force` to replace the folder |
| `Remote branch ... not found`                                  | the branch or tag does not exist on GitHub (or is not pushed yet)              |
| `Unit tests failed: no firmware built`                         | the branch's unit tests fail; details in `output/logs/tests.txt`               |
| `No repository known for ...`                                  | a library's `.mpy` files contain no repository URL: add it to `FALLBACK_REPOSITORIES` in `docker/builder/constants.py` |
| `Source of ... not found`                                      | a library's repository has no source file with that name at that version       |
| `Firmware build failed`                                        | details in `output/logs/build_release.log` (for example: the firmware does not fit into flash) |
| No RAM measurement                                             | the branch has no memory monitoring lines in `process.py` (section 8)          |
| First run takes long                                           | the Docker image is built once (about 30 minutes)                              |
| `... is not inside the project folder`                         | `--sources` and `--output` must be inside this folder (the container only sees this folder) |

All files created by the build belong to your user, although the build runs as root inside the container.


## 13. Cleaning up

The output and the sources are replaced on every run. To remove everything the build created:

    rm -rf output pyswitch
    docker image rm pyswitch-builder     # the image (about 3.5 GB)
    docker builder prune                 # Docker's build cache (affects all your Docker images)


## 14. Limitations

- **CircuitPython 7.3.1 only**, for RP2040 devices (board `raspberry_pi_pico`, as for the official CircuitPython UF2 used on the PaintAudio MIDI Captain). CircuitPython 8 has less memory on the RP2040, and CircuitPython 9 needs newer library versions.
- The libraries are built in the versions of the branch's `.mpy` files; their `.mpy` files must contain the version (Adafruit libraries do).
- The RAM measurement runs without a connected MIDI device.
- The build is a separate tool: it does not change PySwitch, and it works with any branch that has PySwitch's usual folder layout (`content/`, `test/`, `examples/`).
