import os

from builder import drive
from .helpers import TempTestCase, write

class TestDrive(TempTestCase):

    def test_collect(self):
        c = self.path("content")
        for f in ("boot.py", "code.py", "config.py", "fonts/H20.pcf", "lib/pyswitch/a.py", "lib/misc/n.mpy", "lib/single.mpy",
                  "lib/adafruit_hid/k.mpy", "lib/functools.py", "toc.php", "lib/toc.php", "lib/pyswitch/__pycache__/a.pyc"):
            write(os.path.join(c, f), "x")
        f = self.path("frozen")
        for name in ("pyswitch/a.py", "misc/n.py", "single.py", ".git/HEAD"):
            write(os.path.join(f, name), "x")

        entries = drive.collect(c, f, self.path("drive"))

        self.assertEqual(entries, ["boot.py", "code.py", "config.py", "fonts/", "lib/", "lib/adafruit_hid/", "lib/functools.py"])
        self.assertFalse(os.path.exists(self.path("drive", "toc.php")))
        self.assertTrue(os.path.exists(self.path("content", "lib", "pyswitch", "a.py")))      # content unchanged
