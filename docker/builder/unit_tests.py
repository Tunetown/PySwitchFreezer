import os
import re
import shutil
import tempfile

from . import files, shell

# Package name of PySwitch's test folder in the test layout: Debian's Python has its own package "test" (the tests of
# PySwitch only use relative imports, so the name does not matter)
TEST_PACKAGE = "pyswitch_test"

# Result of the unit tests
class TestResult:
    def __init__(self, ok, tests, coverage, output, html = None):
        self.ok = ok                    # all tests passed
        self.tests = tests              # number of tests run
        self.coverage = coverage        # total coverage (e.g. "98%"), or "" if the tests failed
        self.output = output            # output of unittest
        self.html = html                # folder of the coverage report (HTML), or None if not created

    # One line for the report
    def summary(self):
        if self.ok:
            return f"OK, { self.tests } tests, coverage { self.coverage }"
        failed = re.search(r"FAILED \(([^)]*)\)", self.output)
        return f"FAILED ({ failed.group(1) if failed else 'error' }), { self.tests } tests"

# Runs the Python unit tests of PySwitch with coverage, in the layout of PySwitch's own test container
# (test/compose.yaml: <root>/lib and <root>/test). lib is copied, not linked (coverage would not count linked files).
# With html, the coverage report is also written as HTML into this folder (like test/run of PySwitch; also when tests fail).
def run(pyswitch, html = None):
    root = tempfile.mkdtemp()
    try:
        shutil.copytree(os.path.join(pyswitch, "content", "lib"), os.path.join(root, "lib"), ignore = shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(pyswitch, "test"), os.path.join(root, TEST_PACKAGE), ignore = shutil.ignore_patterns("__pycache__", "report"))

        rc = files.read_text(os.path.join(root, TEST_PACKAGE, ".coveragerc"))
        rc = rc.replace("/project/test", os.path.join(root, TEST_PACKAGE)).replace("/project", root)
        rc = re.sub(r"^include_namespace_packages.*$", "", rc, flags = re.M)          # not known by Debian's coverage version
        rc_file = os.path.join(root, "coveragerc")
        files.write_text(rc_file, rc)

        result = shell.run(["python3", "-m", "coverage", "run", "--rcfile=" + rc_file, "-m", "unittest", "discover", "-t", root, "-s", os.path.join(root, TEST_PACKAGE, "pyswitch")],
                           cwd = root, capture = True, check = False)
        output = result.stdout + result.stderr
        ran = re.search(r"Ran ([0-9]+) tests?", output)
        tests = int(ran.group(1)) if ran else 0

        html_folder = None
        if html:
            created = shell.run(["python3", "-m", "coverage", "html", "--rcfile=" + rc_file, "-d", os.path.abspath(html)], cwd = root, capture = True, check = False)
            html_folder = os.path.abspath(html) if created.returncode == 0 else None

        if result.returncode != 0:
            return TestResult(False, tests, "", output, html_folder)

        report = shell.run(["python3", "-m", "coverage", "report", "--rcfile=" + rc_file], cwd = root, capture = True).stdout
        total = re.search(r"^TOTAL\s.*?([0-9]+%)\s*$", report, re.M)
        return TestResult(True, tests, total.group(1) if total else "?", output, html_folder)

    finally:
        shutil.rmtree(root, ignore_errors = True)
