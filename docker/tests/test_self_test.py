import os
from unittest.mock import patch, MagicMock

from builder import self_test
from .helpers import TempTestCase, write

class TestSelfTest(TempTestCase):

    # Runs self_test.run with shell.run mocked. Returns (exit code, commands).
    def run_self_test(self, tests_returncode = 0, html_returncode = 0, owner = None, args = ()):
        commands = []
        def run(command, cwd = None, capture = False, check = True, env = None, **kwargs):
            commands.append(command)
            result = MagicMock()
            result.returncode, result.stdout = 0, ""
            if "run" in command and "unittest" in command:
                self.seen_env = env
                result.returncode = tests_returncode
            elif "html" in command:
                self.assertFalse(os.path.exists(self.path("out", "test_report", "old.html")))     # old report removed before
                write(command[command.index("-d") + 1] + "/index.html", "")
                result.returncode = html_returncode
            elif "report" in command:
                result.stdout = "Name   Stmts   Miss  Cover\nTOTAL    500     20    96%\n"
            return result
        write(self.path("out", "test_report", "old.html"), "")
        with patch("builder.shell.run", side_effect = run):
            code = self_test.run(list(args), owner = owner, output_folder = self.path("out"))
        return code, commands

    def test_runs_tests_with_coverage(self):
        code, commands = self.run_self_test(args = ["-v"])
        self.assertEqual(code, 0)
        self.assertIn("--source=builder", commands[0])
        self.assertEqual(commands[0][-1], "-v")                              # unittest arguments passed on
        self.assertTrue(self.seen_env["COVERAGE_FILE"].endswith(".coverage"))
        self.assertFalse(os.path.exists(os.path.dirname(self.seen_env["COVERAGE_FILE"])))   # data removed afterwards

    def test_report_replaced(self):
        code, commands = self.run_self_test()
        html = [c for c in commands if "html" in c][0]
        self.assertEqual(html[html.index("-d") + 1], self.path("out", "test_report"))
        self.assertTrue(os.path.exists(self.path("out", "test_report", "index.html")))
        self.assertFalse(os.path.exists(self.path("out", "test_report", "old.html")))
        self.assertIn("Coverage 96%", self.printed())
        self.assertIn("TESTS OK", self.printed())

    def test_report_also_when_tests_fail(self):
        code, commands = self.run_self_test(tests_returncode = 1)
        self.assertEqual(code, 1)
        self.assertIn("TESTS FAILED", self.printed())
        self.assertNotIn("TESTS OK", self.printed())
        self.assertTrue(any("html" in c for c in commands))

    def test_owner(self):
        code, commands = self.run_self_test(owner = "1000:1000")
        self.assertIn(["chown", "1000:1000", self.path("out")], commands)
        self.assertIn(["chown", "-R", "1000:1000", self.path("out", "test_report")], commands)

    def test_no_owner(self):
        code, commands = self.run_self_test()
        self.assertFalse(any(c[0] == "chown" for c in commands))

    def test_main_arguments(self):
        with patch("builder.self_test.run", return_value = 3) as run:
            with self.assertRaises(SystemExit) as e:
                self_test.main(["--owner", "1:2", "-v"])
        self.assertEqual(e.exception.code, 3)
        run.assert_called_once_with(["-v"], owner = "1:2")

    def test_default_verbose(self):
        code, commands = self.run_self_test()
        self.assertEqual(commands[0][-1], "-v")                              # every test is listed

    def test_steps_printed(self):
        self.run_self_test()
        self.assertIn("=== 1/2 Unit tests of the build program", self.printed())
        self.assertIn("=== 2/2 Coverage report", self.printed())

    def test_coverage_html_fails(self):
        code, commands = self.run_self_test(html_returncode = 1)
        self.assertEqual(code, 0)
        self.assertIn("No coverage report", self.printed())
