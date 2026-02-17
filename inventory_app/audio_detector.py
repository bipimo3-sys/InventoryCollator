import os
from config import SUPPORTED_EXTENSIONS


def is_supported_extension(filepath):
    _, ext = os.path.splitext(filepath.lower())
    return ext in SUPPORTED_EXTENSIONS


def validate_header(filepath):
    try:
        with open(filepath, "rb") as f:
            header = f.read(16)

        if header.startswith(b"ID3"):
            return True
        if header.startswith(b"fLaC"):
            return True
        if header.startswith(b"RIFF"):
            return True

        return True  # fallback allow
    except:
        return False
