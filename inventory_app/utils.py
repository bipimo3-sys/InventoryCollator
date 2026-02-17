import os
import logging
from datetime import datetime
from config import LOG_DIR, LOG_FILE


def ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)


def setup_logging():
    ensure_log_dir()
    log_path = os.path.join(LOG_DIR, LOG_FILE)

    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    logging.getLogger().addHandler(logging.StreamHandler())


def generate_timestamp():
    return datetime.utcnow().isoformat()


def human_size(size):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
