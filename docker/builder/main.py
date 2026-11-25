import argparse
import json
import os
import shutil
import sys
import traceback

from . import drive, files, firmware, frozen, measurement, output, report, shell, sources, unit_tests
from .constants import (ASSETS_FOLDER, BOOTLOADER_NAME, DEFAULT_BRANCH, DRIVE_FOLDER_NAME, FIRMWARE_NAME, LOGS_FOLDER_NAME,
                        MEASURE_SECONDS, OUTPUT_FOLDER, PROJECT_FOLDER, REPORT_NAME, REPOSITORY_URL, SOURCES_FOLDER,
                        TEST_REPORT_FOLDER_NAME)

# Number of steps (for the progress output)
_STEPS = 6

# Parses the command line arguments (see ../../build)
def parse_arguments(argv):
    parser = argparse.ArgumentParser(prog = "build", description = "Builds an optimized UF2 image from PySwitch.")
    parser.add_argument("branch", nargs = "?", default = None,
                        help = f"branch or tag of PySwitch to fetch (default: use the existing sources folder as it is; if there is none, fetch { DEFAULT_BRANCH })")
    parser.add_argument("--repository", default = REPOSITORY_URL, help = f"Git repository to fetch PySwitch from (default: { REPOSITORY_URL })")
    parser.add_argument("--force", action = "store_true", help = "with a branch: replace the sources folder even if it was not created by the build")
    parser.add_argument("--sources", default = SOURCES_FOLDER, help = "sources folder (inside the project folder)")
    parser.add_argument("--output", default = OUTPUT_FOLDER, help = "output folder (inside the project folder)")
    parser.add_argument("--measure", action = "store_true", help = "measure the free RAM on an emulated RP2040 (off by default; builds a second, debug firmware and takes about 2 minutes more)")
    parser.add_argument("--example", default = None, help = "measure the RAM with this example configuration (path relative to examples/ of PySwitch; switches on --measure)")
    parser.add_argument("--owner", default = None, help = "uid:gid the created files are given to (set by the build launcher)")
    return parser.parse_args(argv)

# Progress of the build: the current step (for the error message)
class _Progress:
    def __init__(self):
        self.number = 0
        self.text = ""
        self.timer = None

    # Starts the next step: prints the duration of the previous one and the header of the new one
    def step(self, text):
        self.done()
        self.number += 1
        self.text = text
        self.timer = output.Timer()
        output.step(self.number, _STEPS, text)

    # Prints the duration of the current step
    def done(self):
        if self.timer:
            output.info(f"(step { self.number } took { self.timer.text() })")
            self.timer = None

# Path for the output (relative to the project folder, as the user sees it)
def _show(path):
    return os.path.relpath(path, PROJECT_FOLDER)

# Runs the build. Returns the exit code.
def build(args, progress = None):
    progress = progress or _Progress()
    measure = args.measure or bool(args.example)
    output_folder = os.path.abspath(args.output)
    logs = os.path.join(output_folder, LOGS_FOLDER_NAME)
    work = os.path.join(output_folder, ".work")

    progress.step("PySwitch sources")
    src = sources.prepare(args.repository, args.branch, args.sources, force = args.force)
    content = os.path.join(args.sources, "content")

    shutil.rmtree(output_folder, ignore_errors = True)
    os.makedirs(logs)
    os.makedirs(work)
    output.info(f"Output folder { _show(output_folder) }/ cleared")

    progress.step("Unit tests of PySwitch (with coverage)")
    tests = unit_tests.run(args.sources, html = os.path.join(output_folder, TEST_REPORT_FOLDER_NAME))
    files.write_text(os.path.join(logs, "tests.txt"), tests.summary() + "\n\n" + tests.output)
    output.info(tests.summary())
    output.info(f"Test output: { _show(logs) }/tests.txt")
    if tests.html:
        output.info(f"Coverage report: { _show(tests.html) }/index.html")
    if not tests.ok:
        raise shell.BuildError(f"Unit tests failed: no firmware built (details: { _show(logs) }/tests.txt)")

    progress.step("Firmware")
    output.info("Collecting the modules to freeze (PySwitch and the libraries it imports)")
    modules = frozen.prepare(content, os.path.join(work, "frozen_release"))
    files.write_text(os.path.join(logs, "frozen_modules.json"), json.dumps(modules, indent = 1))
    for package in sorted({ m["package"] for m in modules }):
        versions = sorted({ m["version"] for m in modules if m["package"] == package and m["version"] })
        output.info(f"  frozen: { package }" + (f" { ', '.join(versions) }" if versions else ""))

    timer = output.Timer()
    output.info(f"Compiling the release firmware (log: { _show(logs) }/build_release.log)")
    flash = firmware.build(os.path.join(work, "frozen_release"), os.path.join(output_folder, FIRMWARE_NAME), os.path.join(logs, "build_release.log"))
    output.info(f"{ FIRMWARE_NAME } done in { timer.text() }: " + (f"flash used { flash.used } B of { flash.total } B" if flash else "flash use unknown"))

    debug_uf2 = None
    if measure:
        try:
            frozen.debug_copy(os.path.join(work, "frozen_release"), os.path.join(work, "frozen_debug"))
            debug_uf2 = os.path.join(work, "debug.uf2")
            timer = output.Timer()
            output.info(f"Compiling the debug firmware for the RAM measurement (log: { _show(logs) }/build_debug.log)")
            firmware.build(os.path.join(work, "frozen_debug"), debug_uf2, os.path.join(logs, "build_debug.log"))
            output.info(f"Debug firmware done in { timer.text() }")
        except frozen.NoMemoryMonitoring as e:
            output.info(f"No debug firmware: { e }")
            debug_uf2 = None

    progress.step("Drive files")
    drive_folder = os.path.join(output_folder, DRIVE_FOLDER_NAME)
    entries = drive.collect(content, os.path.join(work, "frozen_release"), drive_folder)
    for entry in entries:
        output.info(entry)

    progress.step("RAM measurement (emulated RP2040)")
    result = None
    if not measure:
        output.info("Skipped (off by default; switch it on with --measure)")
    elif debug_uf2:
        example = os.path.join(args.sources, "examples", args.example) if args.example else None
        output.info(f"Configuration: { args.example or 'default (content/)' }; running until loaded, then { MEASURE_SECONDS } s (log: { _show(logs) }/measurement.txt)")
        result = measurement.measure(drive_folder, debug_uf2, os.path.join(logs, "measurement.txt"), example = example)
        output.info(f"Free after loading: { result['loadedFree'] } B, result: { result['status'] }" if result else f"No result (details: { _show(logs) }/measurement.txt)")
    else:
        output.info("Skipped (no debug firmware)")

    progress.step("Report")
    text = report.text(args.repository, src, tests, flash, modules, entries, result, args.example or "default configuration (content/)")
    files.write_text(os.path.join(output_folder, REPORT_NAME), text)
    shutil.copy(os.path.join(ASSETS_FOLDER, BOOTLOADER_NAME), os.path.join(output_folder, BOOTLOADER_NAME))
    shutil.rmtree(work, ignore_errors = True)
    output.info(f"{ _show(output_folder) }/{ REPORT_NAME }")
    output.info(f"{ _show(output_folder) }/{ BOOTLOADER_NAME } (puts the device into bootloader mode)")
    progress.done()
    return 0

# Gives the created files to the user of the host (the container runs as root)
def _give_to_owner(owner, folders):
    if not owner:
        return
    for folder in folders:
        if os.path.exists(folder):
            shell.run(["chown", "-R", owner, folder], check = False)

# Entry point. Prints a clear result line at the end; exit code 0 = success, 1 = failure.
def main(argv = None):
    args = parse_arguments(sys.argv[1:] if argv is None else argv)
    progress = _Progress()
    timer = output.Timer()
    code = 1
    try:
        code = build(args, progress)
        output.block(f"\nBUILD OK in { timer.text() }: { _show(os.path.abspath(args.output)) }/\n"
                     f"  { FIRMWARE_NAME } -> RPI-RP2 drive (bootloader mode: open { BOOTLOADER_NAME } in Chrome/Edge), contents of { DRIVE_FOLDER_NAME }/ -> device drive (MIDICAPTAIN or CIRCUITPY). Report: { REPORT_NAME }, see README.md")
    except shell.BuildError as e:
        output.block(f"\nBUILD FAILED in step { progress.number }/{ _STEPS } ({ progress.text }) after { timer.text() }:\n{ e }")
    except Exception as e:
        output.block(f"\nBUILD FAILED in step { progress.number }/{ _STEPS } ({ progress.text }) after { timer.text() }: unexpected error\n{ traceback.format_exc() }")
    finally:
        _give_to_owner(args.owner, [args.output, args.sources])
    sys.exit(code)
