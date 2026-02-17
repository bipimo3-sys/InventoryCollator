import hashlib
from config import HASH_CHUNK_SIZE


def sha256_file(filepath):
    sha = hashlib.sha256()

    with open(filepath, "rb") as f:
        while True:
            data = f.read(HASH_CHUNK_SIZE)
            if not data:
                break
            sha.update(data)

    return sha.hexdigest()
