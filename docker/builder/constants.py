# Constants of the PySwitch build. Paths are paths inside the build container (the project folder is mounted at /work).

# PySwitch repository and the branch built when no branch is given
REPOSITORY_URL = "https://github.com/Tunetown/PySwitch.git"
DEFAULT_BRANCH = "main"

# Folders (inside the container)
PROJECT_FOLDER = "/work"                                   # project folder (repository root of the build project)
SOURCES_FOLDER = "/work/pyswitch"                          # PySwitch sources, fetched (not versioned)
OUTPUT_FOLDER = "/work/output"                             # build results (not versioned)
SCRIPTS_FOLDER = "/work/docker/scripts"                    # measure.mts, ramprobe.py

# File marking a sources folder created by the build (other folders are not deleted without --force)
SOURCES_MARKER = ".pyswitch_build"

# Output
FIRMWARE_NAME = "PySwitch.uf2"                             # firmware in the output folder
DRIVE_FOLDER_NAME = "drive"                                # drive files in the output folder
REPORT_NAME = "REPORT.md"                                  # report in the output folder
LOGS_FOLDER_NAME = "logs"                                  # logs in the output folder

# Files of PySwitch's content folder which are not copied to the drive (only used by the web emulator)
WEB_ONLY_FILES = ("toc.php",)

# CircuitPython build
CIRCUITPYTHON_VERSION = "7.3.1"
CIRCUITPYTHON_FOLDER = "/opt/circuitpython"                # sources in the image
CIRCUITPYTHON_BOARD = "raspberry_pi_pico"                  # same RP2040 board as the official UF2 for the MIDI Captain

# Repositories of libraries whose .mpy files contain no repository URL (package or module name -> URL)
FALLBACK_REPOSITORIES = {
    "pymidibridge": "https://github.com/Tunetown/PyMidiBridge.git"
}

# Folders of library repositories which never contain library sources
LIBRARY_SKIP_FOLDERS = ("examples", "docs", "tests", "test", "utils", ".git", "js")

# The commented lines in lib/pyswitch/process.py which switch on the memory monitoring (debug firmware)
MEMORY_LINES = ("# from pyswitch.stats import Memory as _Memory", "# _Memory.start()")

# Name of the RAM probe on the drive of the measurement (imported by the debug firmware)
PROBE_MODULE = "_ramprobe"

# RAM measurement
MEASURE_SECONDS = 10                                       # emulated run time after loading
MEASURE_TIMEOUT = 900                                      # real time limit (seconds)
TSX = ["/opt/rp2040js/node_modules/.bin/tsx", "--tsconfig", "/opt/rp2040js/tsconfig.json"]
