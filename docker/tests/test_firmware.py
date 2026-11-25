import os
from unittest.mock import patch, MagicMock

from builder import firmware, shell
from builder.files import read_text, write_text
from .helpers import TempTestCase, write

# Lines of shared-module/usb_midi/__init__.c of CircuitPython 7.3.1
USB_MIDI_C = """static const char midi_streaming_interface_name[] = USB_INTERFACE_NAME " MIDI";
static const char midi_audio_control_interface_name[] = USB_INTERFACE_NAME " Audio";
static const char midi_in_jack_name[] = USB_INTERFACE_NAME " usb_midi.ports[0]";
static const char midi_out_jack_name[] = USB_INTERFACE_NAME " usb_midi.ports[0]";
"""

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
        with patch("builder.shell.run", side_effect = run) as mock, patch("builder.firmware.set_usb_midi_names") as names:
            use = firmware.build(self.path("frozen"), self.path("out.uf2"), self.path("build.log"))
        names.assert_called_once_with("/opt/circuitpython/shared-module/usb_midi/__init__.c", firmware.USB_MIDI_NAMES)
        command = mock.call_args.args[0]
        self.assertIn("BOARD=raspberry_pi_pico", command)
        self.assertIn("FROZEN_MPY_DIRS=" + self.path("frozen"), command)
        self.assertEqual(read_text(self.path("out.uf2")), "UF2")
        self.assertEqual(use.used, 930272)

    def test_build_fails(self):
        result = MagicMock()
        result.returncode = 2
        with patch("builder.shell.run", return_value = result), patch("builder.firmware.set_usb_midi_names"):
            with self.assertRaises(shell.BuildError):
                firmware.build(self.path("frozen"), self.path("out.uf2"), self.path("build.log"))
        self.assertFalse(os.path.exists(self.path("out.uf2")))

    def test_usb_midi_names_like_paintaudio(self):
        # The names of PaintAudio's midicpPico.uf2 (claude/004 TBC 4)
        self.assertEqual(firmware.USB_MIDI_NAMES, {
            "midi_streaming_interface_name": "Midi Captain- MIDI",
            "midi_audio_control_interface_name": "Midi Captain- MIDI ",
            "midi_in_jack_name": "Midi Captain- usb_midi.ports[0]",
            "midi_out_jack_name": "Midi Captain- usb_midi.ports[0]",
        })

    def test_set_usb_midi_names(self):
        source = self.path("usb_midi.c")
        write(source, USB_MIDI_C)
        firmware.set_usb_midi_names(source, firmware.USB_MIDI_NAMES)
        firmware.set_usb_midi_names(source, firmware.USB_MIDI_NAMES)     # again: same result
        self.assertEqual(read_text(source),
            'static const char midi_streaming_interface_name[] = "Midi Captain- MIDI";\n'
            'static const char midi_audio_control_interface_name[] = "Midi Captain- MIDI ";\n'
            'static const char midi_in_jack_name[] = "Midi Captain- usb_midi.ports[0]";\n'
            'static const char midi_out_jack_name[] = "Midi Captain- usb_midi.ports[0]";\n')

    def test_set_usb_midi_names_escapes(self):
        source = self.path("usb_midi.c")
        write(source, USB_MIDI_C)
        firmware.set_usb_midi_names(source, {"midi_in_jack_name": 'a "b" \\c'})
        self.assertIn('midi_in_jack_name[] = "a \\"b\\" \\\\c";', read_text(source))

    def test_set_usb_midi_names_missing(self):
        source = self.path("usb_midi.c")
        write(source, "nothing\n")
        with self.assertRaises(shell.BuildError):
            firmware.set_usb_midi_names(source, {"midi_in_jack_name": "x"})
