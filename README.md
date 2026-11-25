# Build an optimized UF2 image from PySwitch

Builds an optimized UF2 image from PySwitch: one command fetches a branch of [PySwitch](https://github.com/Tunetown/PySwitch) from GitHub, runs its unit tests, builds a CircuitPython 7.3.1 firmware with PySwitch and its libraries already inside, and collects everything you need to copy onto the device, and writes a report. Optionally (`--measure`) it also measures how much RAM is left on an emulated device.

**Why**: normally CircuitPython compiles PySwitch on the device at every start and keeps the compiled program in RAM. In this firmware, PySwitch and its libraries are precompiled and stored in the flash memory of the chip, so **87.5 KiB more RAM** stay free for your configuration (compared to stock PySwitch 2.4.10).

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

Builds the PySwitch sources in `pyswitch/` as they are; if there is no `pyswitch/` folder, the branch `main` is fetched from GitHub first. The first run takes about 30 minutes (the Docker image with CircuitPython, the compiler and the emulator is built once); every later run takes about 30 seconds (with `--measure` about 2.5 minutes). When it is done:

1. Copy `output/PySwitch.uf2` to the device in bootloader mode (drive `RPI-RP2`, section 5).
2. Copy the contents of `output/drive/` to the device drive (MIDI Captain: hold switch 1 while switching on; drive `MIDICAPTAIN`).

Before the first installation: make a backup (section 5).

The build shows every step with its duration and ends with `BUILD OK` or `BUILD FAILED` (with the step and the reason). `output/REPORT.md` shows what was built.


## 2. Requirements

| Needed          | Remark                                                                            |
|-----------------|-----------------------------------------------------------------------------------|
| Linux or macOS  | with `bash` (on Windows: WSL)                                                     |
| Docker          | with Docker Compose (`docker compose`); everything else runs inside the container |
| Internet access | the build fetches PySwitch and the library sources from GitHub                    |
| Disk space      | a few GB for the Docker image                                                     |

Works on x86_64 and ARM64 (aarch64) machines. `git`, Python and the compilers are **not** needed on your machine.


## 3. Usage

    ./build [<branch>] [options]

| Argument / option    | Meaning                                                                                                                                                                                                    |
|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `<branch>`           | branch or tag of PySwitch to fetch into `pyswitch/`. Without it, an existing `pyswitch/` is built as it is (nothing is fetched or changed); if there is none, `main` is fetched                            |
| `--measure`          | also measure the free RAM on an emulated RP2040 (section 8; off by default, takes about 2 minutes more)                                                                                                    |
| `--example <path>`   | measure the RAM with an example configuration instead of the default one (path relative to `examples/` of PySwitch; switches on `--measure`); the drive files in the output keep the default configuration |
| `--repository <url>` | Git repository to fetch PySwitch from (default: the official PySwitch repository), e.g. your fork                                                                                                          |
| `--force`            | with a branch: replace `pyswitch/` even if it was not created by the build (it contains your own files: section 12)                                                                                        |
| `--sources <folder>` | use another sources folder (default `pyswitch/`; must be inside this project folder)                                                                                                                       |
| `--output <folder>`  | use another output folder (default `output/`; must be inside this project folder)                                                                                                                          |
| `--help`             | show the options                                                                                                                                                                                           |

Examples:

    ./build                                            # pyswitch/ as it is (or main if there is no pyswitch/)
    ./build dev_midi                                   # fetch another branch into pyswitch/
    ./build v2.4.10                                    # fetch a tag
    ./build --repository https://github.com/me/PySwitch.git my_branch   # a branch of a fork
    ./build --measure                                  # with RAM measurement
    ./build --example "Kemper Profiler/MIDICaptain 10/Expression Pedals and Wheel"

**Sources folder `pyswitch/`**:

| `pyswitch/`                  | `./build`          | `./build <branch>`                              |
|------------------------------|--------------------|-------------------------------------------------|
| does not exist               | fetches `main`     | fetches the branch                              |
| fetched by an earlier build  | builds it as it is | replaces it by the branch                       |
| your own (e.g. with changes) | builds it as it is | stops with a message (never deleted; `--force`) |

The build stops with `BUILD FAILED` (and builds nothing more) if the branch does not exist or the unit tests fail; the message names the step and the reason. Details of each step are in `output/logs/`.


## 4. Output

Everything is written to `output/` (deleted and created again on every run):

| File / folder     | Content                                                                                                                                                                                                                                      |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PySwitch.uf2`    | the firmware: CircuitPython 7.3.1 with PySwitch and its libraries built in                                                                                                                                                                   |
| `drive/`          | the files for the device drive (section 5)                                                                                                                                                                                                   |
| `REPORT.md`       | sources (branch, commit), unit tests, flash use, frozen modules with versions, drive files, RAM measurement                                                                                                                                  |
| `bootloader.html` | page that puts the device into bootloader mode (section 5)                                                                                                                                                                                   |
| `logs/`           | details: `tests.txt` (unit test output), `build_release.log` (firmware build), `frozen_modules.json` (every frozen module with its source); with `--measure` also `build_debug.log` (debug firmware) and `measurement.txt` (RAM measurement) |
| `test_report/`    | coverage report as HTML (open `index.html` in the browser) of the tests that ran last: PySwitch's unit tests (`./build`) or the tests of the build program (`./test`, section 10)                                                            |

The PySwitch sources of the build are in `pyswitch/` (a shallow clone of the branch; replaced on the next run).


## 5. Installing on the device

For the PaintAudio MIDI Captain (all models). PySwitch runs on PaintAudio's firmware [`midicpPico.uf2`](https://cdn.shopify.com/s/files/1/0656/8312/8548/files/midicpPico.uf2?v=1684781580) (PaintAudio firmware up to version 4): CircuitPython 7.3.1, the same as in `PySwitch.uf2`. So the files on the device drive stay when you install `PySwitch.uf2`, and the device looks the same to the computer (same USB MIDI names).

**Two modes** (connect the device via USB, then switch it on):

| Mode       | How                                                                                           | Drive on the computer                      |
|------------|-----------------------------------------------------------------------------------------------|--------------------------------------------|
| USB setup  | hold switch 1 while switching on                                                              | `MIDICAPTAIN` (or `CIRCUITPY`): your files |
| Bootloader | open `output/bootloader.html` in Chrome or Edge, click the button, select the device ("Pico") | `RPI-RP2`: takes a firmware (`.uf2`)       |

Bootloader mode without the browser (Linux): `stty -F /dev/ttyACM0 1200`. It cannot damage anything; switching the device off and on leaves it.

**Install**

1. **Backup**: in USB setup mode copy everything on the drive to your computer, and download [`midicpPico.uf2`](https://cdn.shopify.com/s/files/1/0656/8312/8548/files/midicpPico.uf2?v=1684781580) (your current firmware).
2. **Firmware**: in bootloader mode copy `output/PySwitch.uf2` to `RPI-RP2`. The device restarts by itself. (macOS: if the Finder reports an error, use `cp -X output/PySwitch.uf2 /Volumes/RPI-RP2/`.)
3. **Drive**: in USB setup mode copy the contents of `output/drive/` to the drive (overwrite), then your own configuration files. `lib/pyswitch` and the libraries built into the firmware can be deleted (they are ignored, section 7).
4. Eject the drive, wait until it is unmounted, switch the device off and on.

**Update**: a new configuration is copied to the drive as before. A new PySwitch version: build it and repeat steps 2–4.

**Going back**: in bootloader mode copy `midicpPico.uf2` to `RPI-RP2`, then install PySwitch on the drive as described in the PySwitch README (or restore your drive backup).

**PaintAudio firmware 5** is not CircuitPython (PySwitch does not run on it). Coming from it, the drive is empty after step 2 (the computer may ask to format it: FAT); then continue with step 3 and copy PySwitch's files from `output/drive/`. Going back to firmware 5: PaintAudio's update instructions in the firmware 5 package.

**Multiboot** (PaintAudio firmware 4 selected by a switch at start, see PySwitch's `examples/Multiboot`) works the same way: put PaintAudio's files and the contents of `output/drive/` on the drive (instead of PySwitch's `content/`), then the `code.py` of the example. PaintAudio's firmware runs with the libraries built into `PySwitch.uf2` (same versions as in PaintAudio's firmware 4.0) and gets more free RAM too; its license is not affected. Not possible with PaintAudio firmware 5 (not CircuitPython).

Other RP2040 boards: bootloader mode usually with the BOOT button held while connecting USB; the drive is called `CIRCUITPY`.


## 6. What the build does

| Step | What happens                                                                                                                                                                                                                                           |
|------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1    | **Fetch** the branch from GitHub into `pyswitch/`                                                                                                                                                                                                      |
| 2    | **Unit tests** of PySwitch (with coverage), coverage report as HTML in `test_report/`; if they fail, the build stops                                                                                                                                   |
| 3    | **Firmware**: PySwitch and the libraries it imports are compiled into CircuitPython 7.3.1 → `PySwitch.uf2`; with `--measure` also a second, debug firmware with PySwitch's memory monitoring switched on (only for the measurement, not in the output) |
| 4    | **Drive files**: the `content/` folder of PySwitch without the built-in modules → `drive/`                                                                                                                                                             |
| 5    | **RAM measurement** (only with `--measure`): the debug firmware and the drive files run on an emulated RP2040                                                                                                                                          |
| 6    | **Report**: `REPORT.md`; `bootloader.html` is copied to the output                                                                                                                                                                                     |

**CircuitPython itself is not changed**, except for the names of the USB MIDI port, which are set like in PaintAudio's firmware ("Midi Captain- MIDI"; setting in `docker/builder/constants.py`). Building Python modules into the firmware ("freezing") is a standard feature of the CircuitPython build, also used by official boards for their libraries. The firmware is a complete CircuitPython 7.3.1; PySwitch and its libraries are additions.


## 7. Frozen modules

**Which**: PySwitch itself and every library of PySwitch's `content/lib` that PySwitch imports, in its core or in any of its actions (for example `adafruit_display_text`, `adafruit_bitmap_font`, `adafruit_hid`, NeoPixel, ST7789, PyMidiBridge). Libraries that PySwitch does not import stay on the drive. The exact list of a build is in `REPORT.md`.

**Versions**: the build uses exactly the library versions of the branch: it reads the version and the repository of each library from its `.mpy` files in `content/lib` and builds the library from its source code at that version. If a version tag does not exist, the default branch of the library is used, and the report says so.

**Search order**: CircuitPython looks for a module first in the root folder of the drive, then in the firmware, then in `lib/`. Consequences:

- A `lib/pyswitch` (or a built-in library) on the drive is **ignored**: the firmware version is used.
- A **newer PySwitch or library version needs a new firmware** (run the build again).
- A `pyswitch` folder in the **root folder** of the drive overrides the built-in PySwitch (section 9).


## 8. The report and the RAM measurement

With `./build --measure` (off by default) the RAM is measured on an **emulated RP2040** (the [rp2040js](https://github.com/wokwi/rp2040js) emulator running the real CircuitPython firmware): the same firmware, the same bytecode and the same memory management as on the device, so the values after loading match the device exactly. The measurement runs the debug firmware (identical to `PySwitch.uf2`, plus PySwitch's memory monitoring) with the drive files, without a connected MIDI device, for 10 seconds of emulated time after loading.

| Value in the report         | Meaning                                                                           |
|-----------------------------|-----------------------------------------------------------------------------------|
| Heap                        | total memory for Python objects                                                   |
| Free at start               | free memory when PySwitch starts                                                  |
| Free at "Showing UI"        | free memory after the configuration has been loaded, before the display is set up |
| **Free after loading**      | free memory when PySwitch is ready: the main value                                |
| Largest free block          | largest piece of memory that can be allocated at once (fragmentation)             |
| Minimum free during the run | lowest free memory during the 10 s run                                            |

The measured configuration is the default configuration of `content/`, or the example given with `--example`. With a connected device (rig names, MIDI traffic) PySwitch needs some more memory at runtime than in the measurement.

The measurement needs the two commented memory monitoring lines in PySwitch's `lib/pyswitch/process.py`; if a branch does not have them, the build skips the measurement and says so.


## 9. Developing PySwitch with this firmware

1. Change the Python code of PySwitch as usual (unit tests and the web emulator work on the `.py` files as before).
2. Run `./build`: it builds your sources in `pyswitch/` as they are (nothing needs to be pushed). Or push a branch and run `./build <branch>` (needs a `pyswitch/` created by the build, or none).
3. Install the output (section 5).

To **try a change on the device without a new firmware**, copy PySwitch's `content/lib/pyswitch` to the **root folder** of the drive (`/pyswitch`, not `/lib/pyswitch`): it overrides the built-in version. This needs as much RAM as PySwitch without this firmware, so large configurations may not fit. Delete `/pyswitch` afterwards.


## 10. Tests of the build program

    ./test            # unit tests of the build program
    ./test -v         # with the name of every test

Runs the unit tests of the build program (`docker/tests`) in the build container. They replace `git`, the CircuitPython build and the emulator by mocks, so they need no network and take about a second. Every test is listed (`-v` by default), then the total coverage and `TESTS OK` or `TESTS FAILED`; the coverage report (HTML) replaces `output/test_report/`. (The unit tests of **PySwitch** are run by `./build`, see `output/logs/tests.txt`; their coverage report also goes to `output/test_report/`, so the folder always holds the report of the tests that ran last.)


## 11. Project layout and configuration

| Path                  | Content                                                                                 |
|-----------------------|-----------------------------------------------------------------------------------------|
| `build`               | the command (starts the build program in its container)                                 |
| `test`                | runs the tests of the build program                                                     |
| `docker/Dockerfile`   | the Docker image: CircuitPython 7.3.1 sources, ARM compiler, Python, Node with rp2040js |
| `docker/compose.yaml` | the container (mounts this folder at `/work`)                                           |
| `docker/builder/`     | the build program (Python), one module per step                                         |
| `docker/tests/`       | tests of the build program                                                              |
| `docker/scripts/`     | RAM measurement (`measure.mts`) and the memory probe used by it                         |
| `pyswitch/`           | PySwitch sources of the last build (not versioned)                                      |
| `output/`             | output of the last build (not versioned)                                                |

**Configuration**: all settings are constants in `docker/builder/constants.py`: the PySwitch repository URL, the default branch, the folders, the output names, repositories of libraries whose `.mpy` files contain no repository URL, the USB MIDI names of the firmware (`USB_MIDI_NAMES`; empty: the official names of CircuitPython), and the duration of the RAM measurement.


## 12. Troubleshooting

| Message / problem                                                                           | Cause and solution                                                                                                                                                                                         |
|---------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `pyswitch/ exists and was not created by the build, so it is not replaced by branch ...`    | you gave a branch, but `pyswitch/` contains your own sources; the build never deletes them. Build them as they are with `./build` (without a branch), move the folder away, or use `--force` to replace it |
| `Remote branch ... not found` (then `BUILD FAILED ... Command failed (128): git clone ...`) | the branch or tag does not exist on GitHub (or is not pushed yet)                                                                                                                                          |
| `... does not look like PySwitch: ... is missing`                                           | `pyswitch/` exists but has no `content/lib/pyswitch/` or `test/`                                                                                                                                           |
| `Example not found: ...`                                                                    | the path given with `--example` does not exist in `examples/` of the branch                                                                                                                                |
| `Unit tests failed: no firmware built`                                                      | the branch's unit tests fail; details in `output/logs/tests.txt`, coverage in `output/test_report/`                                                                                                        |
| `No repository known for ...`                                                               | a library's `.mpy` files contain no repository URL: add it to `FALLBACK_REPOSITORIES` in `docker/builder/constants.py`                                                                                     |
| `Source of ... not found`                                                                   | a library's repository has no source file with that name at that version                                                                                                                                   |
| `Firmware build failed`                                                                     | details in `output/logs/build_release.log` (for example: the firmware does not fit into flash)                                                                                                             |
| No RAM measurement                                                                          | it is off by default: use `--measure`; with it, the branch has no memory monitoring lines in `process.py` (section 8)                                                                                      |
| `BUILD FAILED ...: unexpected error` with a traceback                                       | an error in the build program itself: please report it with the output                                                                                                                                     |
| Warning `Docker Compose is configured to build using Bake, but buildx isn't installed`      | harmless; Docker builds the image without the buildx plugin                                                                                                                                                |
| First run takes long                                                                        | the Docker image is built once (about 30 minutes)                                                                                                                                                          |
| `... is not inside the project folder`                                                      | `--sources` and `--output` must be inside this folder (the container only sees this folder)                                                                                                                |

All files created by the build belong to your user, although the build runs as root inside the container.


## 13. Cleaning up

The output and the sources are replaced on every run. To remove everything the build created:

    rm -rf output pyswitch
    docker image rm pyswitch-builder     # the image
    docker builder prune                 # Docker's build cache (affects all your Docker images)


## 14. Limitations

- **CircuitPython 7.3.1 only**, for RP2040 devices (built like the official CircuitPython UF2 for the board `raspberry_pi_pico`). CircuitPython 8 has less memory on the RP2040, and CircuitPython 9 needs newer library versions.
- The libraries are built in the versions of the branch's `.mpy` files; their `.mpy` files must contain the version (Adafruit libraries do).
- The RAM measurement runs without a connected MIDI device.
- The build is a separate tool: it does not change PySwitch, and it works with any branch that has PySwitch's usual folder layout (`content/`, `test/`, `examples/`).
