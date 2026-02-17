# ---------------------------------------------------------------------------------------------------
# audio_detector.py=================>
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

# ===========================>

# ---------------------------------------------------------------------------------------------------
# config.py=================>
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

# ===========================>

# ---------------------------------------------------------------------------------------------------
# db.py=================>
import sqlite3
from config import DB_FILE


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS drives (
            id INTEGER PRIMARY KEY,
            drive_key TEXT UNIQUE,
            root_path TEXT,
            created_at TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            drive_key TEXT,
            relative_path TEXT,
            file_size INTEGER,
            sha256 TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            duration REAL,
            bitrate INTEGER,
            created_at TEXT,
            UNIQUE(drive_key, relative_path)
        )
        """)

        self.conn.commit()

    def insert_drive(self, drive_key, root_path, created_at):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO drives (drive_key, root_path, created_at) VALUES (?, ?, ?)",
            (drive_key, root_path, created_at),
        )
        self.conn.commit()

    def insert_file(self, data):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO files (
            drive_key, relative_path, file_size, sha256,
            title, artist, album, duration, bitrate, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        self.conn.commit()

    def close(self):
        self.conn.close()

# ===========================>

# ---------------------------------------------------------------------------------------------------
# drive_manager.py=================>
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

# ===========================>

# ---------------------------------------------------------------------------------------------------
# hasher.py=================>
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

# ===========================>

# ---------------------------------------------------------------------------------------------------
# __init__.py=================>

# ===========================>

# ---------------------------------------------------------------------------------------------------
# main.py=================>
import os
from utils import setup_logging, generate_timestamp
from drive_manager import get_or_create_drive_key
from scanner import scan_drive
from db import Database


def show_menu():
    print("=== Inventory Collator ===")
    drive = input("Enter drive root path (e.g. E:\\): ").strip()

    print("1. Test Mode")
    print("2. New Drive")
    print("3. Resume / Update")

    mode = input("Select mode: ").strip()

    return drive, mode


def main():
    setup_logging()

    drive_root, mode = show_menu()

    if not os.path.exists(drive_root):
        print("Drive path not found.")
        return

    force_new = (mode == "2")
    test_mode = (mode == "1")

    drive_key, created = get_or_create_drive_key(drive_root, force_new=force_new)

    db = Database()
    db.insert_drive(drive_key, drive_root, generate_timestamp())

    scan_drive(db, drive_root, drive_key, test_mode=test_mode)

    db.close()

    print("Scan complete.")
    print("Log file created in /logs folder.")


if __name__ == "__main__":
    main()

# ===========================>

# ---------------------------------------------------------------------------------------------------
# metadata_extractor.py=================>
import os

try:
    from mutagen import File as MutagenFile
except:
    MutagenFile = None


def extract_metadata(filepath):
    metadata = {
        "title": None,
        "artist": None,
        "album": None,
        "duration": None,
        "bitrate": None,
    }

    if MutagenFile:
        try:
            audio = MutagenFile(filepath)
            if audio:
                metadata["duration"] = getattr(audio.info, "length", None)
                metadata["bitrate"] = getattr(audio.info, "bitrate", None)

                if audio.tags:
                    metadata["title"] = str(audio.tags.get("TIT2", [None])[0])
                    metadata["artist"] = str(audio.tags.get("TPE1", [None])[0])
                    metadata["album"] = str(audio.tags.get("TALB", [None])[0])
        except:
            pass

    # Fallback: derive from filename
    if not metadata["title"]:
        metadata["title"] = os.path.splitext(os.path.basename(filepath))[0]

    return metadata

# ===========================>

# ---------------------------------------------------------------------------------------------------
# scanner.py=================>
import os
import logging
from audio_detector import is_supported_extension, validate_header
from metadata_extractor import extract_metadata
from hasher import sha256_file
from utils import generate_timestamp
from config import TEST_MODE_FILE_LIMIT


def scan_drive(db, drive_root, drive_key, test_mode=False):
    total_files = 0
    processed = 0

    for root, dirs, files in os.walk(drive_root):
        for file in files:
            total_files += 1

    print(f"Total files detected: {total_files}")

    for root, dirs, files in os.walk(drive_root):
        for file in files:
            full_path = os.path.join(root, file)

            relative_path = os.path.relpath(full_path, drive_root)

            if not is_supported_extension(full_path):
                continue

            if not validate_header(full_path):
                continue

            try:
                size = os.path.getsize(full_path)
                sha = sha256_file(full_path)
                metadata = extract_metadata(full_path)

                db.insert_file((
                    drive_key,
                    relative_path,
                    size,
                    sha,
                    metadata["title"],
                    metadata["artist"],
                    metadata["album"],
                    metadata["duration"],
                    metadata["bitrate"],
                    generate_timestamp(),
                ))

                processed += 1

                print(f"Processed: {processed}")
                logging.info(f"Processed {relative_path}")

                if test_mode and processed >= TEST_MODE_FILE_LIMIT:
                    print("Test mode limit reached.")
                    return

            except Exception as e:
                logging.error(f"Error processing {relative_path}: {e}")

# ===========================>

# ---------------------------------------------------------------------------------------------------
# utils.py=================>
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

# ===========================>

