import os
from unittest.mock import patch, MagicMock

from builder import main, shell, frozen, unit_tests, firmware
import contextlib
import io

from builder.files import read_text
from .helpers import TempTestCase

class TestMain(TempTestCase):

    # The progress output of the build is not shown in the test output
    def setUp(self):
        super().setUp()
        self.silence = contextlib.ExitStack()
        self.silence.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.silence.enter_context(contextlib.redirect_stderr(io.StringIO()))

    def tearDown(self):
        self.silence.close()
        super().tearDown()

    def test_arguments(self):
        args = main.parse_arguments(["dev", "--force", "--example", "Kemper/X"])
        self.assertEqual((args.branch, args.force, args.example), ("dev", True, "Kemper/X"))
        args = main.parse_arguments([])
        self.assertEqual((args.branch, args.force, args.example, args.sources, args.output), ("main", False, None, "/work/pyswitch", "/work/output"))

    # Runs main.build with all steps mocked. Returns the mocks.
    def run_build(self, tests_ok = True, debug_possible = True):
        args = main.parse_arguments(["--sources", self.path("src"), "--output", self.path("out")])
        mocks = {}
        with patch("builder.sources.fetch", return_value = "abc1234") as mocks["fetch"], \
             patch("builder.unit_tests.run", return_value = unit_tests.TestResult(tests_ok, 3, "90%" if tests_ok else "", "output")) as mocks["tests"], \
             patch("builder.frozen.prepare", return_value = []) as mocks["prepare"], \
             patch("builder.firmware.build", return_value = firmware.FlashUse(1, 2, 3)) as mocks["firmware"], \
             patch("builder.drive.collect", return_value = ["boot.py"]) as mocks["drive"], \
             patch("builder.measurement.measure", return_value = { "loadedFree": 5, "status": "OK" }) as mocks["measure"], \
             patch("builder.report.text", return_value = "REPORT") as mocks["report"]:
            if not debug_possible:
                mocks["prepare"].side_effect = lambda content, out, debug = False: (_ for _ in ()).throw(frozen.NoMemoryMonitoring("no lines")) if debug else []
            mocks["result"] = main.build(args)
        return mocks

    def test_all_steps(self):
        m = self.run_build()
        self.assertEqual(m["result"], 0)
        self.assertEqual(m["firmware"].call_count, 2)                    # release and debug firmware
        self.assertTrue(m["prepare"].call_args_list[1].kwargs.get("debug"))
        self.assertEqual(m["measure"].call_count, 1)
        self.assertEqual(read_text(self.path("out", "REPORT.md")), "REPORT")
        self.assertTrue(os.path.exists(self.path("out", "logs", "tests.txt")))
        self.assertFalse(os.path.exists(self.path("out", ".work")))

    def test_tests_failed_no_firmware(self):
        with self.assertRaises(shell.BuildError):
            self.run_build(tests_ok = False)

    def test_tests_failed_no_firmware_calls(self):
        args = main.parse_arguments(["--sources", self.path("src"), "--output", self.path("out")])
        with patch("builder.sources.fetch", return_value = "abc"), \
             patch("builder.unit_tests.run", return_value = unit_tests.TestResult(False, 3, "", "FAILED (failures=1)")), \
             patch("builder.firmware.build") as build:
            with self.assertRaises(shell.BuildError):
                main.build(args)
        build.assert_not_called()

    def test_no_memory_monitoring_no_measurement(self):
        m = self.run_build(debug_possible = False)
        self.assertEqual(m["result"], 0)
        self.assertEqual(m["firmware"].call_count, 1)
        m["measure"].assert_not_called()

    def test_main_exit_code_and_owner(self):
        with patch("builder.main.build", side_effect = shell.BuildError("bad")), patch("builder.shell.run") as run:
            with self.assertRaises(SystemExit) as e:
                main.main(["--owner", "1000:1000", "--output", self.path("out"), "--sources", self.path("src")])
        self.assertEqual(e.exception.code, 1)
