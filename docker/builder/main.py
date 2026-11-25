import argparse
import json
import os
import shutil
import sys

from . import drive, files, firmware, frozen, measurement, report, shell, sources, unit_tests
from .constants import (DEFAULT_BRANCH, DRIVE_FOLDER_NAME, FIRMWARE_NAME, LOGS_FOLDER_NAME, OUTPUT_FOLDER,
                        REPORT_NAME, REPOSITORY_URL, SOURCES_FOLDER)

# Number of steps (for the progress output)
_STEPS = 6

# Parses the command line arguments (see ../../build)
def parse_arguments(argv):
    parser = argparse.ArgumentParser(prog = "build", description = "Builds an optimized UF2 image from PySwitch.")
    parser.add_argument("branch", nargs = "?", default = DEFAULT_BRANCH, help = f"branch or tag of PySwitch (default: { DEFAULT_BRANCH })")
    parser.add_argument("--force", action = "store_true", help = "replace the sources folder even if it was not created by the build")
    parser.add_argument("--sources", default = SOURCES_FOLDER, help = "sources folder (inside the project folder)")
    parser.add_argument("--output", default = OUTPUT_FOLDER, help = "output folder (inside the project folder)")
    parser.add_argument("--example", default = None, help = "measure the RAM with this example configuration (path relative to examples/ of PySwitch)")
    parser.add_argument("--owner", default = None, help = "uid:gid the created files are given to (set by the build launcher)")
    return parser.parse_args(argv)

# Prints a step
def _step(number, text):
    print(f"\n=== { number }/{ _STEPS } { text } ===", flush = True)

# Runs the build. Returns the exit code.
def build(args):
    output = os.path.abspath(args.output)
    logs = os.path.join(output, LOGS_FOLDER_NAME)
    work = os.path.join(output, ".work")

    _step(1, f"Fetching PySwitch ({ args.branch }) from { REPOSITORY_URL }")
    commit = sources.fetch(REPOSITORY_URL, args.branch, args.sources, force = args.force)
    print(f"Commit { commit }")
    content = os.path.join(args.sources, "content")

    shutil.rmtree(output, ignore_errors = True)
    os.makedirs(logs)
    os.makedirs(work)

    _step(2, "Running the unit tests")
    tests = unit_tests.run(args.sources)
    files.write_text(os.path.join(logs, "tests.txt"), tests.summary() + "\n\n" + tests.output)
    print(tests.summary())
    if not tests.ok:
        raise shell.BuildError(f"Unit tests failed: no firmware built (log: { os.path.join(logs, 'tests.txt') })")

    _step(3, "Building the firmware")
    modules = frozen.prepare(content, os.path.join(work, "frozen_release"))
    files.write_text(os.path.join(logs, "frozen_modules.json"), json.dumps(modules, indent = 1))
    flash = firmware.build(os.path.join(work, "frozen_release"), os.path.join(output, FIRMWARE_NAME), os.path.join(logs, "build_release.log"))
    print(f"Flash used: { flash.used } B of { flash.total } B" if flash else "Flash use unknown")

    print("Debug firmware for the RAM measurement")
    debug_uf2 = os.path.join(work, "debug.uf2")
    try:
        frozen.prepare(content, os.path.join(work, "frozen_debug"), debug = True)
        firmware.build(os.path.join(work, "frozen_debug"), debug_uf2, os.path.join(logs, "build_debug.log"))
    except frozen.NoMemoryMonitoring as e:
        print(str(e))
        debug_uf2 = None

    _step(4, "Collecting the drive files")
    drive_folder = os.path.join(output, DRIVE_FOLDER_NAME)
    entries = drive.collect(content, os.path.join(work, "frozen_release"), drive_folder)
    print("\n".join(entries))

    _step(5, "Measuring the RAM (emulated RP2040)")
    result = None
    if debug_uf2:
        example = os.path.join(args.sources, "examples", args.example) if args.example else None
        result = measurement.measure(drive_folder, debug_uf2, os.path.join(logs, "measurement.txt"), example = example)
        print(f"Free after loading: { result['loadedFree'] } B, result: { result['status'] }" if result else "No result (log: logs/measurement.txt)")

    _step(6, "Writing the report")
    text = report.text(REPOSITORY_URL, args.branch, commit, tests, flash, modules, entries, result,
                       args.example or "default configuration (content/)")
    files.write_text(os.path.join(output, REPORT_NAME), text)
    shutil.rmtree(work, ignore_errors = True)

    print(f"\nDone: { output }\n  { FIRMWARE_NAME } -> RPI-RP2 drive (bootloader mode), contents of { DRIVE_FOLDER_NAME }/ -> CIRCUITPY drive. Report: { REPORT_NAME }")
    return 0

# Gives the created files to the user of the host (the container runs as root)
def _give_to_owner(owner, folders):
    if not owner:
        return
    for folder in folders:
        if os.path.exists(folder):
            shell.run(["chown", "-R", owner, folder], check = False)

# Entry point
def main(argv = None):
    args = parse_arguments(sys.argv[1:] if argv is None else argv)
    code = 1
    try:
        code = build(args)
    except shell.BuildError as e:
        print(f"ERROR: { e }", file = sys.stderr)
    finally:
        _give_to_owner(args.owner, [args.output, args.sources])
    sys.exit(code)
