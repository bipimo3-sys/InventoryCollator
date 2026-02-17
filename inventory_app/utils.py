import os
import logging
from datetime import datetime
from config import LOG_DIR, LOG_FILE


# --------------------------------------------------
# Logging Setup
# --------------------------------------------------

def ensure_directory(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def setup_logging():
    ensure_directory(LOG_DIR)

    log_path = os.path.join(LOG_DIR, LOG_FILE)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    logging.info("=== InventoryCollator Scan Started ===")


# --------------------------------------------------
# Time Utilities
# --------------------------------------------------

def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds")


# --------------------------------------------------
# Size Formatting
# --------------------------------------------------

def human_readable_size(size_bytes: int) -> str:
    if size_bytes is None:
        return "0 B"

    size = float(size_bytes)

    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} EB"
