import os
import uuid
from config import DRIVE_KEY_FILENAME


def get_drive_key_path(drive_root):
    return os.path.join(drive_root, DRIVE_KEY_FILENAME)


def create_drive_key(drive_root):
    key = str(uuid.uuid4())
    key_path = get_drive_key_path(drive_root)

    with open(key_path, "w") as f:
        f.write(key)

    return key


def read_drive_key(drive_root):
    key_path = get_drive_key_path(drive_root)
    if not os.path.exists(key_path):
        return None

    with open(key_path, "r") as f:
        return f.read().strip()


def get_or_create_drive_key(drive_root, force_new=False):
    existing_key = read_drive_key(drive_root)

    if existing_key and not force_new:
        return existing_key, False

    return create_drive_key(drive_root), True
