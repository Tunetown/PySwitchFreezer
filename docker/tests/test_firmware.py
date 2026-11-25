import os
from unittest.mock import patch, MagicMock

from builder import firmware, shell
from builder.files import read_text, write_text
from .helpers import TempTestCase, write

LOG = "...\n930272 bytes used, 114208 bytes free in flash firmware space out of 1044480 bytes (1020.0kB).\n16476 bytes used, 245668 bytes free in ram for stack and heap out of 262144 bytes (256.0kB).\n"

class TestFirmware(TempTestCase):

    def test_flash_use(self):
        use = firmware.flash_use(LOG)
        self.assertEqual((use.used, use.free, use.total), (930272, 114208, 1044480))
        self.assertIsNone(firmware.flash_use("no info"))

    def test_build(self):
        def run(command, log = None, **kwargs):
            build = [a for a in command if a.startswith("BUILD=")][0][6:]
            write(os.path.join(build, "firmware.uf2"), "UF2")
            write_text(log, LOG)
            result = MagicMock()
            result.returncode = 0
            return result
        with patch("builder.shell.run", side_effect = run) as mock:
            use = firmware.build(self.path("frozen"), self.path("out.uf2"), self.path("build.log"))
        command = mock.call_args.args[0]
        self.assertIn("BOARD=raspberry_pi_pico", command)
        self.assertIn("FROZEN_MPY_DIRS=" + self.path("frozen"), command)
        self.assertEqual(read_text(self.path("out.uf2")), "UF2")
        self.assertEqual(use.used, 930272)

    def test_build_fails(self):
        result = MagicMock()
        result.returncode = 2
        with patch("builder.shell.run", return_value = result):
            with self.assertRaises(shell.BuildError):
                firmware.build(self.path("frozen"), self.path("out.uf2"), self.path("build.log"))
        self.assertFalse(os.path.exists(self.path("out.uf2")))
