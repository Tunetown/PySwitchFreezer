import os
import shutil

from . import files, shell
from .constants import PROJECT_FOLDER, SOURCES_MARKER

# Fetches a branch (or tag) of PySwitch into a folder. Returns the short commit hash.
# The folder is only replaced if it was created by the build (marker file) or force is set.
def fetch(url, branch, folder, force = False):
    if os.path.exists(folder) and not os.path.exists(os.path.join(folder, SOURCES_MARKER)) and not force:
        raise shell.BuildError(f"{ os.path.relpath(folder, PROJECT_FOLDER) } exists and was not created by the build. Remove it or use --force.")

    shutil.rmtree(folder, ignore_errors = True)
    shell.run(["git", "clone", "--quiet", "--depth", "1", "--branch", branch, url, folder])

    commit = shell.run(["git", "-C", folder, "rev-parse", "--short", "HEAD"], capture = True).stdout.strip()

    files.write_text(os.path.join(folder, SOURCES_MARKER), f"branch { branch }, commit { commit }\n")

    return commit
