import os
import shutil

from . import files, libraries, shell
from .constants import MEMORY_LINES, PROBE_MODULE

# Raised when the debug firmware cannot be prepared (process.py has no commented memory monitoring lines)
class NoMemoryMonitoring(shell.BuildError):
    pass

# Prepares the folder with the modules to freeze into the firmware:
#   - PySwitch (content/lib/pyswitch)
#   - every library of content/lib that PySwitch imports (claude/003 TBC 12). Libraries shipped as .mpy are replaced by
#     their sources, in the version of each .mpy file (version and repository URL are read from the .mpy file itself;
#     the values of the package are used if a file has none).
# With debug, the memory monitoring is switched on in pyswitch/process.py and the RAM probe is imported (RAM measurement).
# The folder is made a git repository with a tag (CircuitPython's preprocess_frozen_modules.py calls "git describe" for
# __version__ lines). Returns the list of frozen modules: dicts with package, file, source, version, ref.
def prepare(content, out, debug = False):
    lib = os.path.join(content, "lib")
    shutil.rmtree(out, ignore_errors = True)
    os.makedirs(out)

    shutil.copytree(os.path.join(lib, "pyswitch"), os.path.join(out, "pyswitch"), ignore = shutil.ignore_patterns("__pycache__"))
    modules = [{ "package": "pyswitch", "file": "", "source": "content/lib/pyswitch", "version": "", "ref": "" }]

    repositories = {}         # (url, version) -> (folder, ref)
    try:
        for entry in libraries.imported_libraries(lib):
            modules += _prepare_library(lib, entry, out, repositories)
    finally:
        for folder, ref in repositories.values():
            shutil.rmtree(folder, ignore_errors = True)

    if debug:
        _add_measurement_changes(os.path.join(out, "pyswitch", "process.py"))

    _make_git_repository(out)
    return modules

# Copies the sources of one library entry of lib into out. Returns its module dicts.
def _prepare_library(lib, entry, out, repositories):
    name = os.path.splitext(entry)[0]
    package_version, package_url = libraries.library_source(lib, entry)
    ret = []

    for f in libraries.library_files(lib, entry):
        target = os.path.join(out, f)
        os.makedirs(os.path.dirname(target), exist_ok = True)

        if f.endswith(".py"):
            shutil.copy(os.path.join(lib, f), target)
            ret.append({ "package": name, "file": f, "source": "content/lib/" + f, "version": "", "ref": "" })
            continue

        if not f.endswith(".mpy"):
            continue

        version, url = libraries.mpy_info(os.path.join(lib, f))
        if not url:
            url, version = package_url, version or package_version
        if not url:
            raise shell.BuildError(f"No repository known for { f } (add it to FALLBACK_REPOSITORIES in constants.py)")

        if (url, version) not in repositories:
            repositories[(url, version)] = libraries.clone(url, version)
        repo, ref = repositories[(url, version)]

        module = os.path.splitext(os.path.basename(f))[0]
        package = os.path.basename(os.path.dirname(f)) or name
        source = libraries.find_source(repo, module, package)
        if not source:
            raise shell.BuildError(f"Source of { f } not found in { url } ({ ref })")

        shutil.copy(source, target[:-4] + ".py")
        ret.append({ "package": name, "file": f[:-4] + ".py", "source": url + " " + os.path.relpath(source, repo), "version": version or "", "ref": ref })

    return ret

# Switches on the memory monitoring in process.py and adds the import of the RAM probe
def _add_measurement_changes(process):
    code = files.read_text(process)
    if not all(line in code for line in MEMORY_LINES):
        raise NoMemoryMonitoring("process.py has no commented memory monitoring lines: no debug firmware, no RAM measurement")

    code = code.replace(MEMORY_LINES[0], MEMORY_LINES[0][2:])
    code = code.replace(MEMORY_LINES[1], MEMORY_LINES[1][2:] + "\nimport " + PROBE_MODULE)
    files.write_text(process, code)

# Makes a folder a git repository with one commit and a tag
def _make_git_repository(folder):
    git = ["git", "-c", "user.name=build", "-c", "user.email=build@localhost", "-c", "safe.directory=*"]
    shell.run(git + ["init", "-q"], cwd = folder)
    shell.run(git + ["add", "-A"], cwd = folder)
    shell.run(git + ["commit", "-q", "-m", "frozen modules"], cwd = folder)
    shell.run(git + ["tag", "1.0.0"], cwd = folder)
