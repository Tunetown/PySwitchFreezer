import os
from unittest.mock import patch, MagicMock

from builder import sources, shell
from builder.files import read_text
from .helpers import TempTestCase, write

class TestSources(TempTestCase):

    def fetch(self, folder, force = False):
        def run(command, **kwargs):
            if command[:2] == ["git", "clone"]:
                os.makedirs(command[-1])
            result = MagicMock()
            result.stdout = "abc1234\n"
            return result
        with patch("builder.shell.run", side_effect = run) as mock:
            commit = sources.fetch("https://github.com/x/PySwitch.git", "main", folder, force = force)
        return commit, mock

    def test_fetch_new_folder(self):
        commit, run = self.fetch(self.path("pyswitch"))
        self.assertEqual(commit, "abc1234")
        clone = run.call_args_list[0].args[0]
        self.assertEqual(clone, ["git", "clone", "--quiet", "--depth", "1", "--branch", "main", "https://github.com/x/PySwitch.git", self.path("pyswitch")])
        self.assertEqual(read_text(self.path("pyswitch", ".pyswitch_build")), "branch main, commit abc1234\n")

    def test_refuses_foreign_folder(self):
        write(self.path("pyswitch", "my_work.py"), "important")
        with patch("builder.sources.PROJECT_FOLDER", self.tmp):
            with self.assertRaises(shell.BuildError) as e:
                self.fetch(self.path("pyswitch"))
        self.assertTrue(str(e.exception).startswith("pyswitch exists"))
        self.assertTrue(os.path.exists(self.path("pyswitch", "my_work.py")))

    def test_force_replaces_foreign_folder(self):
        write(self.path("pyswitch", "my_work.py"), "important")
        self.fetch(self.path("pyswitch"), force = True)
        self.assertFalse(os.path.exists(self.path("pyswitch", "my_work.py")))

    def test_replaces_own_folder(self):
        write(self.path("pyswitch", ".pyswitch_build"), "branch old")
        write(self.path("pyswitch", "old.py"), "")
        self.fetch(self.path("pyswitch"))
        self.assertFalse(os.path.exists(self.path("pyswitch", "old.py")))
