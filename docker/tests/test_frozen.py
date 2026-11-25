import json
import os
from unittest.mock import patch

from builder import frozen, shell
from builder.files import read_text
from .helpers import TempTestCase, mpy, write

PROCESS = "x = 1\n# Uncomment these two lines\n# from pyswitch.stats import Memory as _Memory\n# _Memory.start()\ny = 2\n"

class TestFrozen(TempTestCase):

    # Content folder with PySwitch importing a library package with modules of two repositories (like adafruit_misc),
    # a library without URL in its .mpy (like pymidibridge) and an unused library
    def make_content(self, process = PROCESS):
        lib = self.path("content", "lib")
        write(os.path.join(lib, "pyswitch", "process.py"), process)
        write(os.path.join(lib, "pyswitch", "ui.py"), "from misc.neopixel import NeoPixel\nfrom pymidibridge.Bridge import B\n")
        write(os.path.join(lib, "misc", "__init__.py"), "# init\n")
        write(os.path.join(lib, "misc", "neopixel.mpy"), mpy("6.3.6", "https://github.com/a/NeoPixel.git"), binary = True)
        write(os.path.join(lib, "misc", "st7789.mpy"), mpy("1.5.14", "https://github.com/a/ST7789.git"), binary = True)
        write(os.path.join(lib, "pymidibridge", "Bridge.mpy"), mpy("0.6.0"), binary = True)
        write(os.path.join(lib, "unused", "x.mpy"), mpy("1.0.0", "https://github.com/a/Unused.git"), binary = True)
        return self.path("content")

    # Fake clone: creates a repository folder with the source files and remembers the calls
    def fake_clone(self, url, version):
        self.clones.append((url, version))
        repo = self.path("repos", str(len(self.clones)))
        name = url.split("/")[-1][:-4]
        sources = { "NeoPixel": ["neopixel.py"], "ST7789": ["st7789.py"], "PyMidiBridge": ["python/lib/pymidibridge/bridge.py"] }[name]
        for s in sources:
            write(os.path.join(repo, s), f"# source of { s } { version }\n")
        return (repo, version)

    def prepare(self, debug = False, process = PROCESS):
        self.clones = []
        with patch("builder.libraries.clone", side_effect = self.fake_clone), patch("builder.shell.run") as run:
            modules = frozen.prepare(self.make_content(process), self.path("out"), debug = debug)
        return modules, run

    def test_pyswitch_and_imported_libraries(self):
        modules, run = self.prepare()
        out = self.path("out")
        self.assertTrue(os.path.exists(os.path.join(out, "pyswitch", "ui.py")))
        self.assertEqual(read_text(os.path.join(out, "misc", "__init__.py")), "# init\n")
        self.assertEqual(read_text(os.path.join(out, "misc", "neopixel.py")), "# source of neopixel.py 6.3.6\n")
        self.assertEqual(read_text(os.path.join(out, "misc", "st7789.py")), "# source of st7789.py 1.5.14\n")
        self.assertEqual(read_text(os.path.join(out, "pymidibridge", "Bridge.py")), "# source of python/lib/pymidibridge/bridge.py 0.6.0\n")
        self.assertFalse(os.path.exists(os.path.join(out, "unused")))
        self.assertFalse(any(f.endswith(".mpy") for b, d, fs in os.walk(out) for f in fs))

    def test_versions_per_file(self):
        modules, run = self.prepare()
        self.assertEqual(sorted(self.clones), [("https://github.com/Tunetown/PyMidiBridge.git", "0.6.0"), ("https://github.com/a/NeoPixel.git", "6.3.6"), ("https://github.com/a/ST7789.git", "1.5.14")])
        by_file = { m["file"]: m for m in modules }
        self.assertEqual(by_file["misc/neopixel.py"]["version"], "6.3.6")
        self.assertEqual(by_file["misc/st7789.py"]["version"], "1.5.14")
        self.assertEqual(by_file["misc/__init__.py"]["source"], "content/lib/misc/__init__.py")
        json.dumps(modules)

    def test_git_repository(self):
        modules, run = self.prepare()
        commands = [c.args[0] for c in run.call_args_list]
        self.assertTrue(any("init" in c for c in commands))
        self.assertTrue(any("tag" in c and "1.0.0" in c for c in commands))

    def test_release_without_measurement_changes(self):
        self.prepare()
        self.assertEqual(read_text(self.path("out", "pyswitch", "process.py")), PROCESS)

    def test_debug_measurement_changes(self):
        self.prepare(debug = True)
        code = read_text(self.path("out", "pyswitch", "process.py"))
        self.assertIn("\nfrom pyswitch.stats import Memory as _Memory\n_Memory.start()\nimport _ramprobe\n", code)
        self.assertNotIn("# _Memory.start()", code)

    def test_debug_without_memory_lines(self):
        with self.assertRaises(frozen.NoMemoryMonitoring):
            self.prepare(debug = True, process = "x = 1\n")

    def test_source_not_found(self):
        def clone(url, version):
            os.makedirs(self.path("empty"), exist_ok = True)
            return (self.path("empty"), version)
        with patch("builder.libraries.clone", side_effect = clone), patch("builder.shell.run"):
            with self.assertRaises(shell.BuildError):
                frozen.prepare(self.make_content(), self.path("out"))

    def test_debug_copy(self):
        self.prepare()
        with patch("builder.libraries.clone") as clone, patch("builder.shell.run") as run:
            frozen.debug_copy(self.path("out"), self.path("debug"))
        clone.assert_not_called()                                           # no second download
        self.assertIn("import _ramprobe", read_text(self.path("debug", "pyswitch", "process.py")))
        self.assertEqual(read_text(self.path("out", "pyswitch", "process.py")), PROCESS)     # release unchanged
        self.assertEqual(read_text(self.path("debug", "misc", "neopixel.py")), "# source of neopixel.py 6.3.6\n")
        self.assertTrue(any("init" in c.args[0] for c in run.call_args_list))

    def test_debug_copy_without_memory_lines(self):
        self.prepare(process = "x = 1\n")
        with patch("builder.shell.run"):
            with self.assertRaises(frozen.NoMemoryMonitoring):
                frozen.debug_copy(self.path("out"), self.path("debug"))
        self.assertFalse(os.path.exists(self.path("debug")))
