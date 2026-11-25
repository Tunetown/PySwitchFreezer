# Small file helpers (files are always closed)

# Returns the text of a file
def read_text(path):
    with open(path, encoding = "utf-8") as f:
        return f.read()

# Returns the bytes of a file
def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()

# Writes a text file
def write_text(path, text):
    with open(path, "w", encoding = "utf-8") as f:
        f.write(text)
