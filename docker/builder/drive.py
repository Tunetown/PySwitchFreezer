import os
import shutil

from .constants import WEB_ONLY_FILES

# Collects the files for the CIRCUITPY drive: everything of the content folder except the frozen modules (their folders
# or files in lib/, also as .mpy), the web-only files and caches. Returns the drive entries (top level and lib/), sorted.
def collect(content, frozen, out):
    shutil.rmtree(out, ignore_errors = True)
    shutil.copytree(content, out, ignore = shutil.ignore_patterns("__pycache__", *WEB_ONLY_FILES))

    for entry in os.listdir(frozen):
        if entry.startswith("."):
            continue
        name = os.path.splitext(entry)[0]
        for candidate in (entry, name + ".py", name + ".mpy"):
            path = os.path.join(out, "lib", candidate)
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)

    return entries(out)

# Returns the entries of a drive folder: top level and the contents of lib/ (folders with a trailing slash), sorted
def entries(drive):
    ret = []
    for entry in sorted(os.listdir(drive)):
        path = os.path.join(drive, entry)
        ret.append(entry + ("/" if os.path.isdir(path) else ""))
        if entry == "lib" and os.path.isdir(path):
            for sub in sorted(os.listdir(path)):
                ret.append("lib/" + sub + ("/" if os.path.isdir(os.path.join(path, sub)) else ""))
    return ret
