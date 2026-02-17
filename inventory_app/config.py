import os

APP_NAME = "InventoryCollator"

DB_FILE = "inventory.db"
LOG_DIR = "logs"
LOG_FILE = "scan.log"

DRIVE_KEY_FILENAME = ".__MUSIC_ARCHIVE_DRIVE_ID"

SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".wma",
}

HASH_CHUNK_SIZE = 1024 * 1024  # 1MB
TEST_MODE_FILE_LIMIT = 100

SKIP_EXISTING_DEFAULT = True

SCHEMA_VERSION = 1
