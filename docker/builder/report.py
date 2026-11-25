import datetime

from .constants import CIRCUITPYTHON_BOARD, CIRCUITPYTHON_VERSION, FIRMWARE_NAME

# Returns a column-aligned Markdown table
def table(header, rows):
    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = lambda r: "| " + " | ".join(str(r[i]).ljust(widths[i]) for i in range(len(header))) + " |"
    return "\n".join([line(header), "|-" + "-|-".join("-" * w for w in widths) + "-|"] + [line(r) for r in rows])

# Formats a byte count: "<bytes> B (<KiB> KiB)", or "–" if unknown
def size(value):
    return f"{ value } B ({ value / 1024:.1f} KiB)" if isinstance(value, int) and value >= 0 else "–"

# Returns the rows of the frozen packages: (package, number of files, sources with versions)
def package_rows(modules):
    packages = {}
    for m in modules:
        p = packages.setdefault(m["package"], { "files": 0, "sources": set() })
        if m["file"]:
            p["files"] += 1
        source = m["source"].split(" ")[0]
        if m["version"]:
            source += " " + m["version"]
        if m["ref"].startswith("default"):
            source += " (" + m["ref"] + ")"
        p["sources"].add(source)
    return [(f"`{ name }`", str(p["files"]) if p["files"] else "all", ", ".join(sorted(p["sources"]))) for name, p in sorted(packages.items())]

# Returns the text of REPORT.md
def text(url, branch, commit, tests, flash, modules, drive_entries, measurement, configuration, now = None):
    now = now or datetime.datetime.now()
    parts = [f"# PySwitch build report\n\nBuilt { now.strftime('%Y-%m-%d %H:%M') } by `build` (claude/004 Build optimized UF2).\n"]

    parts.append("## Sources\n\n" + table(("Item", "Value"), [
        ("Repository", url), ("Branch", branch), ("Commit", commit),
        ("Firmware", f"CircuitPython { CIRCUITPYTHON_VERSION } ({ CIRCUITPYTHON_BOARD }) with frozen modules"),
    ]) + "\n")

    parts.append(f"## Unit tests\n\n{ tests.summary() }\n")

    if flash:
        parts.append("## Firmware\n\n" + table(("Item", "Value"), [
            ("File", f"`{ FIRMWARE_NAME }`"),
            ("Flash used", f"{ flash.used } B of { flash.total } B ({ flash.used * 100 // flash.total } %)"),
            ("Flash free", f"{ flash.free } B"),
        ]) + "\n")

    parts.append("## Frozen modules\n\nPySwitch and every library of `content/lib` it imports; libraries from their sources in the versions of the `.mpy` files. Details: `logs/frozen_modules.json`.\n\n"
                 + table(("Package", "Files", "Source"), package_rows(modules)) + "\n")

    parts.append("## Drive files (`drive/`)\n\nCopy to the CIRCUITPY drive:\n\n" + "\n".join(f"- `{ e }`" for e in drive_entries) + "\n")

    if measurement:
        m = measurement
        parts.append(f"## RAM measurement\n\nCircuitPython { CIRCUITPYTHON_VERSION } on an emulated RP2040 (rp2040js), debug firmware (same build with PySwitch's memory monitoring switched on), configuration: { configuration }, no MIDI device connected.\n\n" + table(("Value", "Free RAM"), [
            ("Heap", size(m["total"])), ("Free at start", size(m["startFree"])), ("Free at \"Showing UI\"", size(m["showingUi"])),
            ("**Free after loading**", "**" + size(m["loadedFree"]) + "**"), ("Largest free block", size(m["block"])),
            ("Minimum free during the run", size(m["minFree"])), ("Result", m["status"]),
        ]) + "\n")
    else:
        parts.append("## RAM measurement\n\nNot measured (see the output of `build`).\n")

    return "\n".join(parts)
