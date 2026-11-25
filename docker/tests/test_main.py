import os
from unittest.mock import patch

from builder import main, shell, frozen, sources, unit_tests, firmware
from builder.files import read_text
from .helpers import TempTestCase

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
SOURCES = sources.Sources("/work/pyswitch", True, "main", "abc1234", "2.4.10")

class TestMain(TempTestCase):

    def test_arguments(self):
        args = main.parse_arguments(["dev", "--force", "--example", "Kemper/X"])
        self.assertEqual((args.branch, args.force, args.example), ("dev", True, "Kemper/X"))
        args = main.parse_arguments([])
        self.assertEqual((args.branch, args.force, args.measure, args.example, args.sources, args.output), (None, False, False, None, "/work/pyswitch", "/work/output"))
        self.assertTrue(main.parse_arguments(["--measure"]).measure)

    # Arguments of a build into the temporary folder
    def arguments(self, *extra):
        return main.parse_arguments(["--sources", self.path("src"), "--output", self.path("out")] + list(extra))

    # Runs main.build with all steps mocked. Returns the mocks.
    def run_build(self, tests_ok = True, debug_possible = True, html = None, extra = ("--measure",)):
        mocks = {}
        with patch("builder.main.ASSETS_FOLDER", ASSETS), \
             patch("builder.sources.prepare", return_value = SOURCES) as mocks["sources"], \
             patch("builder.unit_tests.run", return_value = unit_tests.TestResult(tests_ok, 3, "90%" if tests_ok else "", "output", html)) as mocks["tests"], \
             patch("builder.frozen.prepare", return_value = [{ "package": "pyswitch", "version": "" }, { "package": "lib_a", "version": "1.2.3" }]) as mocks["prepare"], \
             patch("builder.frozen.debug_copy") as mocks["debug_copy"], \
             patch("builder.firmware.build", return_value = firmware.FlashUse(1, 2, 3)) as mocks["firmware"], \
             patch("builder.drive.collect", return_value = ["boot.py"]) as mocks["drive"], \
             patch("builder.measurement.measure", return_value = { "loadedFree": 5, "status": "OK" }) as mocks["measure"], \
             patch("builder.report.text", return_value = "REPORT") as mocks["report"]:
            if not debug_possible:
                mocks["debug_copy"].side_effect = frozen.NoMemoryMonitoring("no lines")
            mocks["result"] = main.build(self.arguments(*extra))
        return mocks

    def test_all_steps(self):
        m = self.run_build()
        self.assertEqual(m["result"], 0)
        m["sources"].assert_called_once_with("https://github.com/Tunetown/PySwitch.git", None, self.path("src"), force = False)
        self.assertTrue(os.path.exists(self.path("out", "bootloader.html")))
        self.assertEqual(m["firmware"].call_count, 2)                    # release and debug firmware
        self.assertEqual(m["prepare"].call_count, 1)                      # library sources fetched once
        m["debug_copy"].assert_called_once_with(self.path("out", ".work", "frozen_release"), self.path("out", ".work", "frozen_debug"))
        self.assertEqual(m["measure"].call_count, 1)
        self.assertIs(m["report"].call_args.args[1], SOURCES)
        self.assertEqual(read_text(self.path("out", "REPORT.md")), "REPORT")
        self.assertTrue(os.path.exists(self.path("out", "logs", "tests.txt")))
        self.assertFalse(os.path.exists(self.path("out", ".work")))
        self.assertEqual(m["tests"].call_args.kwargs["html"], self.path("out", "test_report"))

    def test_repository_option(self):
        args = main.parse_arguments(["--repository", "https://github.com/me/PySwitch.git", "dev"])
        self.assertEqual((args.repository, args.branch), ("https://github.com/me/PySwitch.git", "dev"))
        self.assertEqual(main.parse_arguments([]).repository, "https://github.com/Tunetown/PySwitch.git")
        with patch("builder.main.REPOSITORY_URL", "unused"):
            m = self.run_build(extra = ("--repository", "https://github.com/me/PySwitch.git"))
        self.assertEqual(m["sources"].call_args.args[0], "https://github.com/me/PySwitch.git")
        self.assertEqual(m["report"].call_args.args[0], "https://github.com/me/PySwitch.git")

    def test_measurement_off_by_default(self):
        m = self.run_build(extra = ())
        self.assertEqual(m["result"], 0)
        self.assertEqual(m["firmware"].call_count, 1)                    # only the release firmware
        m["debug_copy"].assert_not_called()
        m["measure"].assert_not_called()
        self.assertIsNone(m["report"].call_args.args[6])                 # no measurement result in the report
        self.assertIn("Skipped (off by default; switch it on with --measure)", self.printed())

    def test_example_switches_measurement_on(self):
        m = self.run_build(extra = ("--example", "Kemper/X"))
        self.assertEqual(m["firmware"].call_count, 2)
        self.assertEqual(m["measure"].call_args.kwargs["example"], os.path.join(self.path("src"), "examples", "Kemper/X"))

    def test_progress_output(self):
        self.run_build(html = self.path("out", "test_report"))
        out = self.printed()
        for number, title in enumerate(["PySwitch sources", "Unit tests of PySwitch", "Firmware", "Drive files", "RAM measurement", "Report"], 1):
            self.assertIn(f"=== { number }/6 { title }", out)
        self.assertIn("OK, 3 tests, coverage 90%", out)
        self.assertIn("frozen: lib_a 1.2.3", out)
        self.assertIn("Compiling the release firmware", out)
        self.assertIn("Free after loading: 5 B, result: OK", out)
        self.assertIn("(step 6 took", out)

    def test_tests_failed_no_firmware(self):
        with patch("builder.sources.prepare", return_value = SOURCES), \
             patch("builder.unit_tests.run", return_value = unit_tests.TestResult(False, 3, "", "FAILED (failures=1)")), \
             patch("builder.firmware.build") as build:
            with self.assertRaises(shell.BuildError) as e:
                main.build(self.arguments())
        build.assert_not_called()
        self.assertIn("Unit tests failed", str(e.exception))

    def test_no_memory_monitoring_no_measurement(self):
        m = self.run_build(debug_possible = False)
        self.assertEqual(m["result"], 0)
        self.assertEqual(m["firmware"].call_count, 1)
        m["measure"].assert_not_called()
        self.assertIn("Skipped (no debug firmware)", self.printed())

    # Error reporting of main(): result line, exit code, files given to the user

    def run_main(self, build_effect):
        with patch("builder.main.build", side_effect = build_effect), patch("builder.shell.run") as run:
            with self.assertRaises(SystemExit) as e:
                main.main(["--owner", "1000:1000", "--output", self.path("out"), "--sources", self.path("src")])
        return e.exception.code, run

    def test_main_ok(self):
        os.makedirs(self.path("out"))
        code, run = self.run_main(lambda args, progress: 0)
        self.assertEqual(code, 0)
        self.assertIn("BUILD OK", self.printed())
        run.assert_called_once_with(["chown", "-R", "1000:1000", self.path("out")], check = False)

    def test_main_build_error(self):
        def fail(args, progress):
            progress.step("PySwitch sources")
            raise shell.BuildError("pyswitch/ exists and was not created by the build")
        os.makedirs(self.path("src"))
        code, run = self.run_main(fail)
        self.assertEqual(code, 1)
        out = self.printed()
        self.assertIn("BUILD FAILED in step 1/6 (PySwitch sources)", out)
        self.assertIn("pyswitch/ exists and was not created by the build", out)
        self.assertNotIn("BUILD OK", out)
        run.assert_called_once_with(["chown", "-R", "1000:1000", self.path("src")], check = False)   # also after an error

    def test_main_unexpected_error(self):
        def fail(args, progress):
            progress.step("PySwitch sources")
            progress.step("Unit tests of PySwitch (with coverage)")
            raise KeyError("boom")
        code, run = self.run_main(fail)
        self.assertEqual(code, 1)
        out = self.printed()
        self.assertIn("BUILD FAILED in step 2/6 (Unit tests of PySwitch (with coverage))", out)
        self.assertIn("unexpected error", out)
        self.assertIn("KeyError: 'boom'", out)                           # traceback for the analysis

    def test_main_error_message_after_step_output(self):
        # The error is printed with print (stdout) like the steps, so it appears after them (user report 2026-11-25)
        def fail(args, progress):
            progress.step("PySwitch sources")
            raise shell.BuildError("bad")
        self.run_main(fail)
        out = self.printed()
        self.assertLess(out.index("=== 1/6 PySwitch sources"), out.index("BUILD FAILED"))
