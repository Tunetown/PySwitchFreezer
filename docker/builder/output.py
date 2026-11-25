import time

# Output of the build program. Everything goes to stdout, so that the order stays as written (docker compose passes
# stdout and stderr on separately; an error on stderr appeared before the step it belongs to, user report 2026-11-25).

# Prints the header of a step
def step(number, total, text):
    print(f"\n=== { number }/{ total } { text } ===", flush = True)

# Prints a line of information within a step
def info(text):
    print("  " + text, flush = True)

# Prints a block of lines (e.g. an error) without indentation
def block(text):
    print(text, flush = True)

# Formats a duration in seconds ("8 s", "2 min 5 s")
def duration(seconds):
    seconds = int(round(seconds))
    return f"{ seconds // 60 } min { seconds % 60 } s" if seconds >= 60 else f"{ seconds } s"

# Measures the time since its creation
class Timer:
    def __init__(self):
        self.start = time.monotonic()

    # Seconds since the start
    def seconds(self):
        return time.monotonic() - self.start

    # Formatted time since the start
    def text(self):
        return duration(self.seconds())
