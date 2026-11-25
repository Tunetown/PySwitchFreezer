import os
import shutil
import tempfile
import unittest

# Writes a file (creating its folders)
def write(path, content = "", binary = False):
    os.makedirs(os.path.dirname(path), exist_ok = True)
    with open(path, "wb" if binary else "w") as f:
        f.write(content)

# Returns the bytes of a fake .mpy file containing a version and/or repository URL string (like real .mpy files)
def mpy(version = None, url = None):
    data = b"M\x05\x02\x1f" + b"\x00" * 8
    if version:
        data += bytes([len(version)]) + version.encode() + b"\x00"
    if url:
        data += bytes([len(url)]) + url.encode() + b"\x00"
    return data + b"\x00" * 4

# Test case with a temporary folder (self.tmp), removed after each test
class TempTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors = True)

    # Path inside the temporary folder
    def path(self, *parts):
        return os.path.join(self.tmp, *parts)
