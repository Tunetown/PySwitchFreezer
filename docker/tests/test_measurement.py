import os
from unittest.mock import patch

from builder import measurement, shell
from builder.files import read_text, write_text
from .helpers import TempTestCase, write

class TestMeasurement(TempTestCase):

    def test_parse_result(self):
        self.assertEqual(measurement.parse_result('Heap: 1\nRESULT_JSON {"loadedFree": 5}\n'), { "loadedFree": 5 })
        self.assertIsNone(measurement.parse_result("no result"))

    def measure(self, example = None):
        write(self.path("drive", "config.py"), "default")
        write(self.path("example", "config.py"), "example")
        self.seen = {}
        def run(command, log = None, **kwargs):
            drive = [a for a in command if a.startswith("--drive=")][0][8:]
            self.seen["files"] = sorted(os.listdir(drive))
            self.seen["config"] = read_text(os.path.join(drive, "config.py"))
            self.seen["command"] = command
            write_text(log, 'RESULT_JSON {"status": "OK", "loadedFree": 135520}\n')
        with patch("builder.shell.run", side_effect = run), patch("builder.measurement.SCRIPTS_FOLDER", self.path("scripts")):
            write(self.path("scripts", "ramprobe.py"), "probe")
            return measurement.measure(self.path("drive"), self.path("debug.uf2"), self.path("m.log"), example = example)

    def test_measure(self):
        result = self.measure()
        self.assertEqual(result, { "status": "OK", "loadedFree": 135520 })
        self.assertEqual(self.seen["files"], ["_ramprobe.py", "config.py"])
        self.assertEqual(self.seen["config"], "default")
        self.assertIn("--uf2=" + self.path("debug.uf2"), self.seen["command"])
        self.assertEqual(read_text(self.path("drive", "config.py")), "default")     # drive files unchanged

    def test_measure_example(self):
        self.measure(example = self.path("example"))
        self.assertEqual(self.seen["config"], "example")

    def test_measure_example_missing(self):
        with self.assertRaises(shell.BuildError):
            self.measure(example = self.path("nothing"))
