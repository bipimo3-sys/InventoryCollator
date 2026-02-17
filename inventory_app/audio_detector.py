import os
import logging
from config import AUDIO_EXTENSIONS


# --------------------------------------------------
# Magic Headers
# --------------------------------------------------

MAGIC_HEADERS = {
    ".mp3": [b"ID3", b"\xff\xfb"],
    ".flac": [b"fLaC"],
    ".wav": [b"RIFF"],
    ".aac": [b"\xff\xf1", b"\xff\xf9"],
    ".ogg": [b"OggS"],
    ".m4a": [b"\x00\x00\x00"],
}


# --------------------------------------------------
# Extension Check
# --------------------------------------------------

def is_extension_allowed(file_name: str) -> bool:
    ext = os.path.splitext(file_name)[1].lower()
    return ext in AUDIO_EXTENSIONS


# --------------------------------------------------
# Header Validation
# --------------------------------------------------

def validate_audio_header(file_path: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in MAGIC_HEADERS:
        return False

    try:
        with open(file_path, "rb") as f:
            header = f.read(16)

        for magic in MAGIC_HEADERS[ext]:
            if header.startswith(magic):
                return True

        return False

    except Exception as e:
        logging.error(f"Header validation failed for {file_path}: {e}")
        return False


# --------------------------------------------------
# Main Check
# --------------------------------------------------

def is_valid_audio(file_path: str) -> bool:
    if not is_extension_allowed(file_path):
        return False

    if not validate_audio_header(file_path):
        logging.warning(f"Header invalid: {file_path}")
        return False

    return True
