import os
from unittest.mock import patch, MagicMock

from builder import unit_tests
from builder.files import read_text
from .helpers import TempTestCase, write

class TestUnitTests(TempTestCase):

    def make_pyswitch(self):
        write(self.path("ps", "content", "lib", "pyswitch", "a.py"), "")
        write(self.path("ps", "test", ".coveragerc"), "[run]\nsource = /project\nomit =\n    /project/test/*\n[report]\ninclude_namespace_packages = True\n")
        write(self.path("ps", "test", "pyswitch", "test_a.py"), "")
        write(self.path("ps", "test", "report", "index.html"), "")
        return self.path("ps")

    def run_tests(self, returncode, stderr, report = "TOTAL   100   2   98%\n"):
        self.seen = {}
        def run(command, cwd = None, **kwargs):
            result = MagicMock()
            if "run" in command:
                rc = [a for a in command if a.startswith("--rcfile=")][0][9:]
                self.seen["rc"] = read_text(rc)
                self.seen["files"] = sorted(os.listdir(cwd))
                result.returncode, result.stdout, result.stderr = returncode, "", stderr
            else:
                result.returncode, result.stdout, result.stderr = 0, report, ""
            return result
        with patch("builder.shell.run", side_effect = run):
            return unit_tests.run(self.make_pyswitch())

    def test_ok(self):
        result = self.run_tests(0, "....\nRan 427 tests in 1.2s\n\nOK\n")
        self.assertTrue(result.ok)
        self.assertEqual((result.tests, result.coverage), (427, "98%"))
        self.assertEqual(result.summary(), "OK, 427 tests, coverage 98%")

    def test_layout_and_coverage_config(self):
        self.run_tests(0, "Ran 1 test in 0.1s\n\nOK\n")
        self.assertEqual(self.seen["files"], ["coveragerc", "lib", "pyswitch_test"])
        self.assertNotIn("/project", self.seen["rc"])
        self.assertNotIn("include_namespace_packages", self.seen["rc"])
        self.assertIn("pyswitch_test/*", self.seen["rc"])

    def test_failed(self):
        result = self.run_tests(1, "F..\nRan 3 tests in 0.1s\n\nFAILED (failures=1)\n")
        self.assertFalse(result.ok)
        self.assertEqual(result.summary(), "FAILED (failures=1), 3 tests")
