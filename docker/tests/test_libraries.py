import os
from unittest.mock import patch

from builder import libraries
from .helpers import TempTestCase, mpy, write

class TestLibraries(TempTestCase):

    def test_mpy_info(self):
        write(self.path("a.mpy"), mpy("2.22.12", "https://github.com/adafruit/Adafruit_CircuitPython_Display_Text.git"), binary = True)
        self.assertEqual(libraries.mpy_info(self.path("a.mpy")), ("2.22.12", "https://github.com/adafruit/Adafruit_CircuitPython_Display_Text.git"))

    def test_mpy_info_without_strings(self):
        write(self.path("a.mpy"), mpy(), binary = True)
        self.assertEqual(libraries.mpy_info(self.path("a.mpy")), (None, None))

    def test_mpy_info_ignores_longer_numbers(self):
        write(self.path("a.mpy"), mpy("1.2.3.4"), binary = True)
        self.assertEqual(libraries.mpy_info(self.path("a.mpy"))[0], None)

    def test_imported_names(self):
        write(self.path("lib", "pyswitch", "a.py"), "from adafruit_display_text import label\nimport board\n  from .x import y\n# from functools import wraps\n")
        write(self.path("lib", "pyswitch", "sub", "b.py"), "    import adafruit_hid.keyboard\n")
        self.assertEqual(libraries.imported_names(self.path("lib")), { "adafruit_display_text", "board", "adafruit_hid" })

    def test_imported_libraries(self):
        write(self.path("lib", "pyswitch", "a.py"), "from adafruit_misc.neopixel import NeoPixel\nimport single\n")
        write(self.path("lib", "adafruit_misc", "neopixel.mpy"), mpy(), binary = True)
        write(self.path("lib", "single.mpy"), mpy(), binary = True)
        write(self.path("lib", "functools.py"), "")
        self.assertEqual(libraries.imported_libraries(self.path("lib")), ["adafruit_misc", "single.mpy"])

    def test_library_files(self):
        write(self.path("lib", "pkg", "a.mpy"), mpy(), binary = True)
        write(self.path("lib", "pkg", "sub", "b.py"), "")
        write(self.path("lib", "pkg", "__pycache__", "c.pyc"), "")
        self.assertEqual(libraries.library_files(self.path("lib"), "pkg"), ["pkg/a.mpy", "pkg/sub/b.py"])
        self.assertEqual(libraries.library_files(self.path("lib"), "single.mpy"), ["single.mpy"])

    def test_library_source_from_mpy(self):
        write(self.path("lib", "pkg", "a.mpy"), mpy("1.5.11", "https://github.com/x/y.git"), binary = True)
        self.assertEqual(libraries.library_source(self.path("lib"), "pkg"), ("1.5.11", "https://github.com/x/y.git"))

    def test_library_source_fallback(self):
        write(self.path("lib", "pymidibridge", "a.mpy"), mpy("0.6.0"), binary = True)
        self.assertEqual(libraries.library_source(self.path("lib"), "pymidibridge"), ("0.6.0", "https://github.com/Tunetown/PyMidiBridge.git"))

    def test_find_source_prefers_package_folder(self):
        write(self.path("repo", "examples", "neopixel.py"), "")
        write(self.path("repo", "neopixel.py"), "")
        write(self.path("repo", "adafruit_misc", "neopixel.py"), "")
        self.assertEqual(libraries.find_source(self.path("repo"), "neopixel", "adafruit_misc"), self.path("repo", "adafruit_misc", "neopixel.py"))

    def test_find_source_case_insensitive(self):
        write(self.path("repo", "python", "lib", "pymidibridge", "pymidibridge.py"), "")
        self.assertEqual(libraries.find_source(self.path("repo"), "PyMidiBridge", "pymidibridge"), self.path("repo", "python", "lib", "pymidibridge", "pymidibridge.py"))

    def test_find_source_not_found(self):
        write(self.path("repo", "tests", "x.py"), "")
        self.assertIsNone(libraries.find_source(self.path("repo"), "x", "pkg"))

    def test_clone_tag(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            class R:
                returncode = 0
            return R()
        with patch("builder.shell.run", side_effect = run):
            folder, ref = libraries.clone("https://github.com/x/y.git", "1.2.3")
        self.assertEqual(ref, "1.2.3")
        self.assertEqual(calls[0][:6], ["git", "clone", "-q", "--depth", "1", "--branch"])
        self.assertEqual(calls[0][6], "1.2.3")
        os.rmdir(folder)

    def test_clone_tag_missing_uses_default_branch(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            class R:
                returncode = 128 if "--branch" in command else 0
            return R()
        with patch("builder.shell.run", side_effect = run):
            folder, ref = libraries.clone("https://github.com/x/y.git", "9.9.9")
        self.assertEqual(ref, "default branch (tag 9.9.9 not found)")
        self.assertNotIn("--branch", calls[1])
        os.rmdir(folder)
