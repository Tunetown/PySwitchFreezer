import os
import re
import shutil
import sys
import tempfile

from . import output, shell
from .constants import OUTPUT_FOLDER, PROJECT_FOLDER, TEST_REPORT_FOLDER_NAME

# Folder of the build program (docker/): working folder of its unit tests
DOCKER_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Title of the coverage report
REPORT_TITLE = "PySwitch build program: unit tests"

# Runs the unit tests of the build program (tests/) with coverage and writes the coverage report as HTML into the
# output folder, replacing the old one. Returns the exit code of the tests.
def run(unittest_args,                  # arguments passed to unittest (e.g. ["-v"])
        owner = None,                   # uid:gid the report is given to (the container runs as root)
        output_folder = OUTPUT_FOLDER   # output folder
    ):
    report = os.path.join(output_folder, TEST_REPORT_FOLDER_NAME)
    data = tempfile.mkdtemp()
    env = dict(os.environ, COVERAGE_FILE = os.path.join(data, ".coverage"))
    coverage = [sys.executable, "-m", "coverage"]
    timer = output.Timer()
    try:
        output.step(1, 2, "Unit tests of the build program (with coverage)")
        tests = shell.run(coverage + ["run", "--source=builder", "-m", "unittest", "discover", "-s", "tests", "-t", "."] + list(unittest_args or ["-v"]),
                          cwd = DOCKER_FOLDER, check = False, env = env)

        output.step(2, 2, "Coverage report")
        shutil.rmtree(report, ignore_errors = True)
        html = shell.run(coverage + ["html", "-q", "-d", report, "--title", REPORT_TITLE], cwd = DOCKER_FOLDER, check = False, env = env)
        text = shell.run(coverage + ["report"], cwd = DOCKER_FOLDER, capture = True, check = False, env = env).stdout
        total = re.search(r"^TOTAL\s.*?([0-9]+%)\s*$", text, re.M)

        if html.returncode == 0:
            output.info(f"Coverage { total.group(1) if total else '?' }, report: { os.path.relpath(report, PROJECT_FOLDER) }/index.html")
        else:
            output.info("No coverage report (coverage html failed)")

        if owner and os.path.exists(report):
            shell.run(["chown", owner, output_folder], check = False)
            shell.run(["chown", "-R", owner, report], check = False)

        output.block(f"\nTESTS OK in { timer.text() }" if tests.returncode == 0 else f"\nTESTS FAILED (see the output above) after { timer.text() }")
        return tests.returncode

    finally:
        shutil.rmtree(data, ignore_errors = True)

# Entry point (called by ../../test): [--owner <uid:gid>] [<unittest arguments; default -v: every test is listed>]
def main(argv = None):
    args = list(sys.argv[1:] if argv is None else argv)
    owner = None
    if args[:1] == ["--owner"]:
        owner, args = args[1], args[2:]
    sys.exit(run(args, owner = owner))

if __name__ == "__main__":
    main()
