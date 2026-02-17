import os

APP_NAME = "InventoryCollator"

# -------------------------
# Database
# -------------------------

DB_FILE = "inventory.db"
SCHEMA_VERSION = 1

# -------------------------
# Logging
# -------------------------

LOG_DIR = "logs"
LOG_FILE = "scan.log"

# -------------------------
# Drive Identity
# -------------------------

DRIVE_KEY_FILENAME = ".__MUSIC_ARCHIVE_DRIVE_ID"

# -------------------------
# Audio Extensions (Default)
# -------------------------

DEFAULT_AUDIO_EXTENSIONS = {
    "mp3",
    "flac",
    "wav",
    "aiff",
    "ogg",
    "m4a",
    "aac",
    "ape",
    "alac",
    "wma",
}

# -------------------------
# Hashing Strategy
# -------------------------

PARTIAL_HASH_SIZE = 8 * 1024 * 1024  # 8 MB
HASH_CHUNK_SIZE = 1024 * 1024        # 1 MB chunks

# -------------------------
# Performance
# -------------------------

BATCH_COMMIT_SIZE = 100
TEST_MODE_FILE_LIMIT = 100

# -------------------------
# Defaults
# -------------------------

DEFAULT_RESCAN_MODE = "skip"  # skip | force
DEFAULT_COMPUTE_FULL_HASH = False
