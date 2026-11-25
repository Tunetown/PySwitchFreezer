import os
import re
import shutil

from . import files, output, shell
from .constants import DEFAULT_BRANCH, PROJECT_FOLDER, SOURCES_MARKER

# Where the PySwitch sources of a build come from
class Sources:
    def __init__(self, folder, fetched, branch, commit, version):
        self.folder = folder            # sources folder
        self.fetched = fetched          # True: fetched from GitHub by this build, False: existing folder used as it is
        self.branch = branch            # branch or tag, or "" if unknown (folder not created by the build)
        self.commit = commit            # short commit hash, or "" if unknown
        self.version = version          # PYSWITCH_VERSION of content/lib/pyswitch/misc.py, or "" if not found

# Prepares the PySwitch sources in a folder (user wish 2026-11-25: "if pyswitch is there, just use it"):
# - no branch given and the folder exists: the folder is used as it is (nothing is changed or fetched);
# - the folder does not exist: the branch (default: DEFAULT_BRANCH) is fetched into it;
# - a branch given and the folder exists: the folder is replaced by the branch, but only if the build created it
#   (marker file) or force is set; a folder of the user is never replaced otherwise.
# Returns a Sources.
def prepare(url, branch, folder, force = False):
    name = os.path.relpath(folder, PROJECT_FOLDER)

    if os.path.exists(folder) and branch is None:
        _check_layout(folder, name)
        marker = _read_marker(folder)
        output.info(f"Using the existing folder { name }/ as it is (nothing fetched)" + (f": branch { marker[0] }, commit { marker[1] }" if marker else ""))
        sources = Sources(folder, False, marker[0] if marker else "", marker[1] if marker else "", _version(folder))

    else:
        branch = branch or DEFAULT_BRANCH
        if os.path.exists(folder):
            if not os.path.exists(os.path.join(folder, SOURCES_MARKER)) and not force:
                raise shell.BuildError(f"{ name }/ exists and was not created by the build, so it is not replaced by branch { branch }.\n"
                                       f"Build it as it is with ./build (without a branch), remove it, or use --force to replace it.")
            output.info(f"Replacing { name }/ (created by an earlier build" + (", --force" if force and not os.path.exists(os.path.join(folder, SOURCES_MARKER)) else "") + ")")
            shutil.rmtree(folder)

        output.info(f"Fetching branch { branch } from { url }")
        shell.run(["git", "clone", "--quiet", "--depth", "1", "--branch", branch, url, folder])
        commit = shell.run(["git", "-C", folder, "rev-parse", "--short", "HEAD"], capture = True).stdout.strip()
        files.write_text(os.path.join(folder, SOURCES_MARKER), f"branch { branch }, commit { commit }\n")
        _check_layout(folder, name)
        sources = Sources(folder, True, branch, commit, _version(folder))

    output.info(f"PySwitch { sources.version or '(version not found)' }")
    return sources

# Checks that a folder contains PySwitch (content/lib/pyswitch and test/)
def _check_layout(folder, name):
    for sub in (os.path.join("content", "lib", "pyswitch"), "test"):
        if not os.path.isdir(os.path.join(folder, sub)):
            raise shell.BuildError(f"{ name }/ does not look like PySwitch: { sub }/ is missing")

# Reads branch and commit from the marker file of the build. Returns (branch, commit) or None.
def _read_marker(folder):
    path = os.path.join(folder, SOURCES_MARKER)
    if not os.path.exists(path):
        return None
    m = re.match(r"branch (.*), commit (.*)", files.read_text(path).strip())
    return (m.group(1), m.group(2)) if m else None

# Reads PYSWITCH_VERSION from content/lib/pyswitch/misc.py. Returns "" if not found.
def _version(folder):
    path = os.path.join(folder, "content", "lib", "pyswitch", "misc.py")
    if not os.path.exists(path):
        return ""
    m = re.search(r'^PYSWITCH_VERSION\s*=\s*"([^"]*)"', files.read_text(path), re.M)
    return m.group(1) if m else ""
