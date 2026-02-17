import os
import json
import uuid
import shutil
import logging
from config import DRIVE_KEY_FILENAME
from utils import utc_now


# --------------------------------------------------
# Drive Key File Handling
# --------------------------------------------------

def get_key_file_path(drive_root: str) -> str:
    return os.path.join(drive_root, DRIVE_KEY_FILENAME)


def read_drive_key_file(drive_root: str):
    key_path = get_key_file_path(drive_root)

    if not os.path.exists(key_path):
        return None

    try:
        with open(key_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        logging.error(f"Failed to read drive key file: {e}")
        return None


def create_drive_key_file(drive_root: str):
    key_data = {
        "drive_key": str(uuid.uuid4()),
        "created_at": utc_now(),
        "version": 1
    }

    key_path = get_key_file_path(drive_root)

    with open(key_path, "w", encoding="utf-8") as f:
        json.dump(key_data, f, indent=4)

    return key_data


# --------------------------------------------------
# Drive Registration Logic
# --------------------------------------------------

def detect_or_register_drive(db, drive_root: str, force_new: bool = False):
    """
    Handles:
    - Reading key file
    - Creating new key if missing
    - Registering drive in DB
    - Updating last_seen, free_bytes, total_bytes
    """

    key_data = read_drive_key_file(drive_root)

    if key_data and not force_new:
        drive_key = key_data["drive_key"]
        logging.info(f"Existing drive key detected: {drive_key}")
    else:
        if force_new:
            logging.info("Force new drive selected.")
        else:
            logging.info("Drive key file missing. Creating new.")

        key_data = create_drive_key_file(drive_root)
        drive_key = key_data["drive_key"]
        logging.info(f"New drive key generated: {drive_key}")

    drive_id = db.get_drive_id_by_key(drive_key)

    total, used, free = shutil.disk_usage(drive_root)

    if drive_id is None:
        drive_id = db.insert_drive(
            drive_key=drive_key,
            volume_serial=None,
            label=None,
            total_bytes=total,
            free_bytes=free,
            status="active"
        )
        logging.info("Drive registered in database.")
    else:
        db.update_drive_stats(
            drive_id=drive_id,
            total_bytes=total,
            free_bytes=free
        )
        logging.info("Drive stats updated.")

    return drive_id, drive_key
