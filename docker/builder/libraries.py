import os
import re
import shutil
import tempfile

from . import files, shell
from .constants import FALLBACK_REPOSITORIES, LIBRARY_SKIP_FOLDERS

# Reads the version and the repository URL from the strings of an .mpy file. Returns (version or None, url or None)
def mpy_info(path):
    data = files.read_bytes(path)
    url = re.search(rb"https://github\.com/[A-Za-z0-9_./-]+?\.git", data)
    version = re.search(rb"(?<![0-9.])([0-9]+\.[0-9]+\.[0-9]+)(?![0-9.])", data)
    return (version.group(1).decode() if version else None, url.group(0).decode() if url else None)

# Returns the top-level names imported by the .py files of lib/pyswitch (absolute imports only)
def imported_names(lib):
    names = set()
    for base, dirs, filenames in os.walk(os.path.join(lib, "pyswitch")):
        for f in filenames:
            if not f.endswith(".py"):
                continue
            for line in files.read_text(os.path.join(base, f)).split("\n"):
                m = re.match(r"\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", line)
                if m:
                    names.add(m.group(1))
    return names

# Returns the entries of lib (folders, .py and .mpy files) which PySwitch imports, sorted
def imported_libraries(lib):
    names = imported_names(lib)
    ret = []
    for entry in sorted(os.listdir(lib)):
        name = re.sub(r"\.(m?py)$", "", entry)
        if name != "pyswitch" and name in names:
            ret.append(entry)
    return ret

# Returns all files of a library entry of lib (a folder or a single file), relative to lib, sorted
def library_files(lib, entry):
    path = os.path.join(lib, entry)
    if not os.path.isdir(path):
        return [entry]
    ret = []
    for base, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in filenames:
            ret.append(os.path.relpath(os.path.join(base, f), lib))
    return sorted(ret)

# Returns the version and repository URL of a library entry: the first found in its .mpy files, the URL from
# FALLBACK_REPOSITORIES if none of them contains one. Returns (version or None, url or None)
def library_source(lib, entry):
    version, url = None, None
    for f in library_files(lib, entry):
        if f.endswith(".mpy"):
            v, u = mpy_info(os.path.join(lib, f))
            version = version or v
            url = url or u
    name = re.sub(r"\.(m?py)$", "", entry)
    return (version, url or FALLBACK_REPOSITORIES.get(name))

# Clones a repository at a tag (or its default branch if the tag does not exist). Returns (folder, ref used).
# The caller removes the folder.
def clone(url, version):
    folder = tempfile.mkdtemp()
    if version and shell.run(["git", "clone", "-q", "--depth", "1", "--branch", version, url, folder], check = False, capture = True).returncode == 0:
        return (folder, version)

    shutil.rmtree(folder, ignore_errors = True)
    folder = tempfile.mkdtemp()
    shell.run(["git", "clone", "-q", "--depth", "1", url, folder])
    return (folder, "default branch" + (f" (tag { version } not found)" if version else ""))

# Finds the source of a module in a cloned repository: a .py file with the same name (case-insensitive), preferably in a
# folder named like the package, otherwise the one with the shortest path. Returns the path or None.
def find_source(repo, module, package):
    candidates = []
    for base, dirs, filenames in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in LIBRARY_SKIP_FOLDERS]
        for f in filenames:
            if f.lower() == module.lower() + ".py":
                candidates.append(os.path.join(base, f))
    if not candidates:
        return None
    candidates.sort(key = lambda c: (os.path.basename(os.path.dirname(c)) != package, len(c)))
    return candidates[0]
