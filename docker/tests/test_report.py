import datetime
import unittest

from builder import report, firmware, sources, unit_tests

FETCHED = sources.Sources("/work/pyswitch", True, "main", "abc1234", "2.4.10")
LOCAL = sources.Sources("/work/pyswitch", False, "", "", "2.4.10")

MODULES = [
    { "package": "pyswitch", "file": "", "source": "content/lib/pyswitch", "version": "", "ref": "" },
    { "package": "misc", "file": "misc/__init__.py", "source": "content/lib/misc/__init__.py", "version": "", "ref": "" },
    { "package": "misc", "file": "misc/neopixel.py", "source": "https://github.com/a/NeoPixel.git neopixel.py", "version": "6.3.6", "ref": "6.3.6" },
    { "package": "bridge", "file": "bridge/b.py", "source": "https://github.com/a/B.git b.py", "version": "0.6.0", "ref": "default branch (tag 0.6.0 not found)" },
]

class TestReport(unittest.TestCase):

    def test_table_aligned(self):
        self.assertEqual(report.table(("A", "Long header"), [("xyz", "1")]), "| A   | Long header |\n|-----|-------------|\n| xyz | 1           |")

    def test_size(self):
        self.assertEqual(report.size(135520), "135520 B (132.3 KiB)")
        self.assertEqual(report.size(-1), "–")

    def test_package_rows(self):
        rows = report.package_rows(MODULES)
        self.assertEqual(rows[0], ("`bridge`", "1", "https://github.com/a/B.git 0.6.0 (default branch (tag 0.6.0 not found))"))
        self.assertEqual(rows[1], ("`misc`", "2", "content/lib/misc/__init__.py, https://github.com/a/NeoPixel.git 6.3.6"))
        self.assertEqual(rows[2], ("`pyswitch`", "all", "content/lib/pyswitch"))

    def test_text(self):
        tests = unit_tests.TestResult(True, 427, "98%", "")
        flash = firmware.FlashUse(930272, 114208, 1044480)
        measurement = { "total": 209088, "startFree": 206912, "showingUi": 150736, "loadedFree": 135520, "block": 131904, "minFree": 135520, "status": "OK" }
        text = report.text("https://github.com/x/PySwitch.git", FETCHED, tests, flash, MODULES, ["boot.py", "lib/"], measurement, "default", now = datetime.datetime(2026, 11, 25, 12, 0))
        self.assertIn("Built 2026-11-25 12:00", text)
        self.assertIn("fetched from https://github.com/x/PySwitch.git", text)
        self.assertIn("| PySwitch version | 2.4.10", text)
        self.assertIn("abc1234", text)
        self.assertIn("OK, 427 tests, coverage 98%", text)
        self.assertIn("930272 B of 1044480 B (89 %)", text)
        self.assertIn("**135520 B (132.3 KiB)**", text)
        self.assertIn("- `lib/`", text)
        self.assertNotIn("Coverage report", text)

    def test_text_with_coverage_report(self):
        tests = unit_tests.TestResult(True, 1, "100%", "", html = "/work/output/test_report")
        text = report.text("u", LOCAL, tests, None, [], [], None, "default")
        self.assertIn("Coverage report: [test_report/index.html](test_report/index.html)", text)

    def test_text_without_measurement(self):
        tests = unit_tests.TestResult(True, 1, "100%", "")
        text = report.text("u", LOCAL, tests, None, [], [], None, "default")
        self.assertIn("Not measured (switched on with `./build --measure`", text)
        self.assertIn("existing sources folder, used as it is", text)
        self.assertIn("| Commit           | unknown", text)
        self.assertNotIn("## Firmware", text)
