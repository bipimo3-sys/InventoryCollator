import hashlib
import logging
from config import HASH_CHUNK_SIZE


def compute_sha256(file_path: str, test_mode: bool = False) -> str | None:
    """
    Computes SHA256 hash of a file using chunked reading.

    If test_mode is True, hashing is skipped (returns None).
    """

    if test_mode:
        return None

    sha256 = hashlib.sha256()

    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(HASH_CHUNK_SIZE)
                if not chunk:
                    break
                sha256.update(chunk)

        return sha256.hexdigest()

    except Exception as e:
        logging.error(f"Hashing failed for {file_path}: {e}")
        return None
