import os
from unittest.mock import patch, MagicMock

from builder import sources, shell
from builder.files import read_text
from .helpers import TempTestCase, write

URL = "https://github.com/x/PySwitch.git"

class TestSources(TempTestCase):

    # Writes a PySwitch folder (minimal layout) with a version
    def make_pyswitch(self, folder, version = "2.4.10", marker = None):
        write(os.path.join(folder, "content", "lib", "pyswitch", "misc.py"), f'# PySwitch version\nPYSWITCH_VERSION = "{ version }"\n')
        write(os.path.join(folder, "test", "test_a.py"), "")
        if marker:
            write(os.path.join(folder, ".pyswitch_build"), marker)

    # Calls sources.prepare with git mocked (a clone creates a PySwitch folder). Returns (Sources, mock).
    def prepare(self, branch, force = False):
        def run(command, **kwargs):
            if command[:2] == ["git", "clone"]:
                self.make_pyswitch(command[-1], version = "2.5.0")
            result = MagicMock()
            result.stdout = "abc1234\n"
            return result
        with patch("builder.shell.run", side_effect = run) as mock, patch("builder.sources.PROJECT_FOLDER", self.tmp):
            result = sources.prepare(URL, branch, self.path("pyswitch"), force = force)
        return result, mock

    def test_existing_folder_used_as_it_is(self):
        self.make_pyswitch(self.path("pyswitch"))
        write(self.path("pyswitch", "my_work.py"), "important")
        src, run = self.prepare(None)
        run.assert_not_called()                                          # nothing fetched
        self.assertFalse(src.fetched)
        self.assertEqual((src.branch, src.commit, src.version), ("", "", "2.4.10"))
        self.assertTrue(os.path.exists(self.path("pyswitch", "my_work.py")))
        self.assertIn("Using the existing folder pyswitch/ as it is", self.printed())

    def test_existing_build_folder_used_with_its_branch(self):
        self.make_pyswitch(self.path("pyswitch"), marker = "branch dev, commit 1111111\n")
        src, run = self.prepare(None)
        run.assert_not_called()
        self.assertEqual((src.fetched, src.branch, src.commit), (False, "dev", "1111111"))

    def test_no_folder_fetches_default_branch(self):
        src, run = self.prepare(None)
        clone = run.call_args_list[0].args[0]
        self.assertEqual(clone, ["git", "clone", "--quiet", "--depth", "1", "--branch", "main", URL, self.path("pyswitch")])
        self.assertEqual((src.fetched, src.branch, src.commit, src.version), (True, "main", "abc1234", "2.5.0"))
        self.assertEqual(read_text(self.path("pyswitch", ".pyswitch_build")), "branch main, commit abc1234\n")

    def test_no_folder_fetches_branch(self):
        src, run = self.prepare("dev")
        self.assertIn("dev", run.call_args_list[0].args[0])
        self.assertEqual(src.branch, "dev")

    def test_branch_replaces_build_folder(self):
        self.make_pyswitch(self.path("pyswitch"), marker = "branch main, commit 1111111\n")
        write(self.path("pyswitch", "old.py"), "")
        src, run = self.prepare("dev")
        self.assertFalse(os.path.exists(self.path("pyswitch", "old.py")))
        self.assertEqual(src.branch, "dev")

    def test_branch_refuses_foreign_folder(self):
        self.make_pyswitch(self.path("pyswitch"))
        write(self.path("pyswitch", "my_work.py"), "important")
        with self.assertRaises(shell.BuildError) as e:
            self.prepare("dev")
        message = str(e.exception)
        self.assertTrue(message.startswith("pyswitch/ exists and was not created by the build"))
        self.assertIn("without a branch", message)                       # tells how to go on
        self.assertTrue(os.path.exists(self.path("pyswitch", "my_work.py")))

    def test_force_replaces_foreign_folder(self):
        self.make_pyswitch(self.path("pyswitch"))
        write(self.path("pyswitch", "my_work.py"), "important")
        src, run = self.prepare("dev", force = True)
        self.assertFalse(os.path.exists(self.path("pyswitch", "my_work.py")))
        self.assertTrue(src.fetched)

    def test_existing_folder_without_pyswitch(self):
        write(self.path("pyswitch", "something.txt"), "")
        with self.assertRaises(shell.BuildError) as e:
            self.prepare(None)
        self.assertIn("does not look like PySwitch", str(e.exception))

    def test_clone_fails(self):
        def run(command, **kwargs):
            raise shell.BuildError("Command failed (128): git clone ...")
        with patch("builder.shell.run", side_effect = run), patch("builder.sources.PROJECT_FOLDER", self.tmp):
            with self.assertRaises(shell.BuildError) as e:
                sources.prepare(URL, "no_such_branch", self.path("pyswitch"))
        self.assertIn("git clone", str(e.exception))

    def test_version_not_found(self):
        write(self.path("pyswitch", "content", "lib", "pyswitch", "misc.py"), "nothing\n")
        write(self.path("pyswitch", "test", "x.py"), "")
        src, run = self.prepare(None)
        self.assertEqual(src.version, "")
        self.assertIn("version not found", self.printed())
