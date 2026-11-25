import json
import os
import re
import shutil
import tempfile

from . import files, shell
from .constants import MEASURE_SECONDS, MEASURE_TIMEOUT, PROBE_MODULE, SCRIPTS_FOLDER, TSX

# Reads the result line of measure.mts ("RESULT_JSON {...}"). Returns the result dict or None.
def parse_result(output):
    m = re.search(r"^RESULT_JSON (.*)$", output, re.M)
    return json.loads(m.group(1)) if m else None

# Measures the RAM of a debug firmware on an emulated RP2040 (measure.mts with rp2040js): the drive files plus the RAM
# probe; with an example folder, its configuration files replace the default configuration (only for the measurement).
# Writes the output of measure.mts to the log. Returns the result dict (see measure.mts) or None if there is none.
def measure(drive, uf2, log, example = None, seconds = MEASURE_SECONDS):
    work = tempfile.mkdtemp()
    try:
        measure_drive = os.path.join(work, "drive")
        shutil.copytree(drive, measure_drive)
        shutil.copy(os.path.join(SCRIPTS_FOLDER, "ramprobe.py"), os.path.join(measure_drive, PROBE_MODULE + ".py"))

        if example:
            if not os.path.isdir(example):
                raise shell.BuildError(f"Example not found: { example }")
            for f in os.listdir(example):
                if f.endswith(".py"):
                    shutil.copy(os.path.join(example, f), os.path.join(measure_drive, f))

        shell.run(TSX + [os.path.join(SCRIPTS_FOLDER, "measure.mts"), "--drive=" + measure_drive, "--uf2=" + uf2,
                         "--seconds=" + str(seconds), "--timeout=" + str(MEASURE_TIMEOUT)], log = log, check = False)

        return parse_result(files.read_text(log))

    finally:
        shutil.rmtree(work, ignore_errors = True)
