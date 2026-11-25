import os
import re
import shutil
import tempfile

from . import files, shell
from .constants import CIRCUITPYTHON_BOARD, CIRCUITPYTHON_FOLDER

# Flash use of a firmware build
class FlashUse:
    def __init__(self, used, free, total):
        self.used = used          # bytes
        self.free = free          # bytes
        self.total = total        # bytes

# Reads the flash use from the log of a CircuitPython build. Returns a FlashUse or None.
def flash_use(log_text):
    m = re.search(r"([0-9]+) bytes used, ([0-9]+) bytes free in flash firmware space out of ([0-9]+) bytes", log_text)
    return FlashUse(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

# Builds CircuitPython for the RP2040 with the modules of a folder frozen into flash (FROZEN_MPY_DIRS; CircuitPython
# itself is not changed). Writes the UF2 and the log. Returns the FlashUse.
def build(frozen, uf2, log):
    build_folder = tempfile.mkdtemp()
    try:
        result = shell.run(["make", "-C", os.path.join(CIRCUITPYTHON_FOLDER, "ports", "raspberrypi"), "BOARD=" + CIRCUITPYTHON_BOARD,
                            "BUILD=" + build_folder, "FROZEN_MPY_DIRS=" + os.path.abspath(frozen), "-j" + str(os.cpu_count() or 1)],
                           log = log, check = False)
        if result.returncode != 0:
            raise shell.BuildError(f"Firmware build failed, log: { log }")

        shutil.copy(os.path.join(build_folder, "firmware.uf2"), uf2)
        return flash_use(files.read_text(log))

    finally:
        shutil.rmtree(build_folder, ignore_errors = True)
