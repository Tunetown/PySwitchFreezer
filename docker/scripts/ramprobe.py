# RAM probe (origin: claude/002 tools/rp2040_ram): copied to the emulated drive as _ramprobe.py by measure.mts and imported by
# lib/pyswitch/process.py right after Memory.start(). Adds raw byte values and the largest free block to the
# output of pyswitch.stats.Memory. Its own RAM is part of every measurement (constant, so differences stay exact).
# Used by ../../build (RAM measurement of the debug firmware).

from gc import collect, mem_free
from pyswitch.stats import Memory

# Set to True by measure.mts to print the loaded modules after loading (used by --profile)
PRINT_MODULES = False

# Returns the size of the largest block that can be allocated (bisection with bytearrays, freed afterwards)
def largest_block():
    collect()
    low = 0
    high = mem_free()
    while low < high:
        size = (low + high + 1) // 2
        try:
            buf = bytearray(size)
            buf = None
            low = size
        except MemoryError:
            high = size - 1
        collect()
    return low

_watch = Memory.watch
_last = [None]

# Replaces Memory.watch: same output, plus a raw line whenever the free RAM changed
def _probe_watch(prefix = None, only_if_changed = False):
    _watch(prefix, only_if_changed)

    free_bytes = Memory.LAST_FREE_BYTES
    if only_if_changed and free_bytes == _last[0]:
        return
    _last[0] = free_bytes

    print(f"RAMPROBE free { free_bytes } { prefix }")

    if prefix == "Application loaded":
        print(f"RAMPROBE block { largest_block() }")

        if PRINT_MODULES:
            import sys
            print("RAMPROBE modules " + " ".join(sys.modules.keys()))

Memory.watch = _probe_watch

print(f"RAMPROBE start { Memory.LAST_FREE_BYTES } { Memory.TOTAL_BYTES }")
