# ---------------------------------------------------------------------------------------------------
# audio_detector.py=================>
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

# ===========================>

# ---------------------------------------------------------------------------------------------------
# config.py=================>
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

# ===========================>

# ---------------------------------------------------------------------------------------------------
# db.py=================>
import sqlite3
import logging
from typing import Optional
from utils import utc_now


class Database:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.create_tables()

    # --------------------------------------------------
    # Schema Creation
    # --------------------------------------------------

    def create_tables(self):
        cursor = self.conn.cursor()

        # Drives
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS drives (
            drive_id INTEGER PRIMARY KEY AUTOINCREMENT,
            drive_key TEXT UNIQUE NOT NULL,
            volume_serial TEXT,
            label TEXT,
            total_bytes INTEGER,
            free_bytes INTEGER,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            last_seen_at TEXT
        )
        """)

        # Files (physical layer)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            drive_id INTEGER,
            relative_path TEXT,
            file_name TEXT,
            extension TEXT,
            size_bytes INTEGER,
            created_at_fs TEXT,
            modified_at_fs TEXT,
            header_valid INTEGER DEFAULT 1,
            sha256 TEXT,
            scan_status TEXT DEFAULT 'active',
            first_seen_at TEXT,
            last_seen_at TEXT,
            FOREIGN KEY(drive_id) REFERENCES drives(drive_id)
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_drive ON files(drive_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_sha ON files(sha256)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(relative_path)")

        # File Path Components
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_path_components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            component_order INTEGER,
            component_name TEXT,
            FOREIGN KEY(file_id) REFERENCES files(file_id)
        )
        """)

        # Audio Metadata
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_audio_metadata (
            file_id INTEGER PRIMARY KEY,
            duration_seconds REAL,
            bitrate INTEGER,
            sample_rate INTEGER,
            channels INTEGER,
            artist TEXT,
            album TEXT,
            title TEXT,
            year TEXT,
            FOREIGN KEY(file_id) REFERENCES files(file_id)
        )
        """)

        self.conn.commit()

    # --------------------------------------------------
    # Drive Methods
    # --------------------------------------------------

    def get_drive_id_by_key(self, drive_key: str) -> Optional[int]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT drive_id FROM drives WHERE drive_key = ?", (drive_key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def insert_drive(self, drive_key, volume_serial, label,
                     total_bytes, free_bytes, status="active"):
        cursor = self.conn.cursor()
        now = utc_now()

        cursor.execute("""
        INSERT INTO drives (drive_key, volume_serial, label,
                            total_bytes, free_bytes, status,
                            created_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            drive_key, volume_serial, label,
            total_bytes, free_bytes, status,
            now, now
        ))

        self.conn.commit()
        return cursor.lastrowid

    def update_drive_stats(self, drive_id, total_bytes, free_bytes):
        now = utc_now()
        self.conn.execute("""
        UPDATE drives
        SET total_bytes = ?, free_bytes = ?, last_seen_at = ?
        WHERE drive_id = ?
        """, (total_bytes, free_bytes, now, drive_id))
        self.conn.commit()

    # --------------------------------------------------
    # File Methods
    # --------------------------------------------------

    def upsert_file(self, drive_id, relative_path, file_name,
                    extension, size_bytes,
                    created_fs, modified_fs,
                    header_valid, sha256):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT file_id FROM files
        WHERE drive_id = ? AND relative_path = ?
        """, (drive_id, relative_path))

        row = cursor.fetchone()
        now = utc_now()

        if row:
            file_id = row[0]
            cursor.execute("""
            UPDATE files
            SET size_bytes = ?, modified_at_fs = ?,
                header_valid = ?, sha256 = ?,
                scan_status = 'active',
                last_seen_at = ?
            WHERE file_id = ?
            """, (
                size_bytes, modified_fs,
                header_valid, sha256,
                now, file_id
            ))
        else:
            cursor.execute("""
            INSERT INTO files (
                drive_id, relative_path, file_name,
                extension, size_bytes,
                created_at_fs, modified_at_fs,
                header_valid, sha256,
                scan_status, first_seen_at, last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """, (
                drive_id, relative_path, file_name,
                extension, size_bytes,
                created_fs, modified_fs,
                header_valid, sha256,
                now, now
            ))
            file_id = cursor.lastrowid

        self.conn.commit()
        return file_id

    def mark_all_files_missing(self, drive_id):
        self.conn.execute("""
        UPDATE files
        SET scan_status = 'missing'
        WHERE drive_id = ?
        """, (drive_id,))
        self.conn.commit()

    def finalize_missing_files(self, drive_id):
        self.conn.execute("""
        UPDATE files
        SET scan_status = 'active'
        WHERE drive_id = ?
          AND scan_status = 'active'
        """)
        self.conn.commit()

    # --------------------------------------------------
    # Path Components
    # --------------------------------------------------

    def insert_path_components(self, file_id, relative_path):
        parts = relative_path.split("/")

        cursor = self.conn.cursor()

        cursor.execute("DELETE FROM file_path_components WHERE file_id = ?", (file_id,))

        for index, part in enumerate(parts):
            cursor.execute("""
            INSERT INTO file_path_components
            (file_id, component_order, component_name)
            VALUES (?, ?, ?)
            """, (file_id, index, part))

        self.conn.commit()

    # --------------------------------------------------
    # Audio Metadata
    # --------------------------------------------------

    def upsert_audio_metadata(self, file_id, metadata: dict):
        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT OR REPLACE INTO file_audio_metadata (
            file_id, duration_seconds, bitrate,
            sample_rate, channels,
            artist, album, title, year
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            metadata.get("duration"),
            metadata.get("bitrate"),
            metadata.get("sample_rate"),
            metadata.get("channels"),
            metadata.get("artist"),
            metadata.get("album"),
            metadata.get("title"),
            metadata.get("year")
        ))

        self.conn.commit()

    # --------------------------------------------------
    # Close
    # --------------------------------------------------

    def close(self):
        self.conn.close()

# ===========================>

# ---------------------------------------------------------------------------------------------------
# drive_manager.py=================>
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

# ===========================>

# ---------------------------------------------------------------------------------------------------
# hasher.py=================>
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

# ===========================>

# ---------------------------------------------------------------------------------------------------
# __init__.py=================>

# ===========================>

# ---------------------------------------------------------------------------------------------------
# main.py=================>
import os
import sys
import logging

from config import DB_PATH
from utils import setup_logging
from db import Database
from drive_manager import detect_or_register_drive
from scanner import Scanner


# --------------------------------------------------
# Menu
# --------------------------------------------------

def show_menu():
    print("\n=== InventoryCollator Phase 1 ===")
    print("1. Test Mode (no hashing)")
    print("2. New Drive (force new key)")
    print("3. Resume / Update Existing Drive")
    print("0. Exit")


def get_drive_input():
    drive = input("Enter drive root (e.g., E:\\ or /media/usb): ").strip()

    if not os.path.exists(drive):
        print("Drive path does not exist.")
        sys.exit(1)

    return drive


def get_mode():
    show_menu()
    choice = input("Select option: ").strip()

    if choice == "1":
        return "test"
    elif choice == "2":
        return "new"
    elif choice == "3":
        return "resume"
    elif choice == "0":
        sys.exit(0)
    else:
        print("Invalid option.")
        sys.exit(1)


# --------------------------------------------------
# Main Execution
# --------------------------------------------------

def main():

    setup_logging()

    logging.info("Application started.")

    drive_root = get_drive_input()
    mode = get_mode()

    test_mode = False
    force_new = False

    if mode == "test":
        test_mode = True
    elif mode == "new":
        force_new = True
    elif mode == "resume":
        pass

    db = Database(DB_PATH)

    drive_id, drive_key = detect_or_register_drive(
        db=db,
        drive_root=drive_root,
        force_new=force_new
    )

    logging.info(f"Drive ID: {drive_id}")
    logging.info(f"Drive Key: {drive_key}")

    scanner = Scanner(
        db=db,
        drive_id=drive_id,
        drive_root=drive_root,
        test_mode=test_mode,
        extract_metadata=True
    )

    scanner.run()

    db.close()

    logging.info("Application finished successfully.")
    print("\nScan complete. Check logs for details.")
    input("Press Enter to exit...")


# --------------------------------------------------

if __name__ == "__main__":
    main()

# ===========================>

# ---------------------------------------------------------------------------------------------------
# metadata_extractor.py=================>
import logging
from mutagen import File as MutagenFile


def extract_audio_metadata(file_path: str) -> dict | None:
    """
    Extracts audio metadata using mutagen.

    Returns dictionary:
    {
        duration,
        bitrate,
        sample_rate,
        channels,
        artist,
        album,
        title,
        year
    }
    """

    try:
        audio = MutagenFile(file_path, easy=True)

        if audio is None:
            return None

        metadata = {
            "duration": None,
            "bitrate": None,
            "sample_rate": None,
            "channels": None,
            "artist": None,
            "album": None,
            "title": None,
            "year": None
        }

        # Technical info
        if hasattr(audio, "info") and audio.info:
            metadata["duration"] = getattr(audio.info, "length", None)
            metadata["bitrate"] = getattr(audio.info, "bitrate", None)
            metadata["sample_rate"] = getattr(audio.info, "sample_rate", None)
            metadata["channels"] = getattr(audio.info, "channels", None)

        # Tags
        if audio.tags:
            metadata["artist"] = _safe_get(audio.tags, "artist")
            metadata["album"] = _safe_get(audio.tags, "album")
            metadata["title"] = _safe_get(audio.tags, "title")
            metadata["year"] = _safe_get(audio.tags, "date") or _safe_get(audio.tags, "year")

        return metadata

    except Exception as e:
        logging.error(f"Metadata extraction failed for {file_path}: {e}")
        return None


def _safe_get(tags, key):
    try:
        value = tags.get(key)
        if isinstance(value, list):
            return value[0]
        return value
    except Exception:
        return None

# ===========================>

# ---------------------------------------------------------------------------------------------------
# scanner.py=================>
import os
import logging
from datetime import datetime

from audio_detector import is_valid_audio
from metadata_extractor import extract_audio_metadata
from hasher import compute_sha256
from utils import human_readable_size


class Scanner:

    def __init__(self, db, drive_id, drive_root,
                 test_mode=False,
                 extract_metadata=True):
        self.db = db
        self.drive_id = drive_id
        self.drive_root = drive_root
        self.test_mode = test_mode
        self.extract_metadata = extract_metadata

        self.total_files = 0
        self.audio_files = 0
        self.total_bytes = 0

    # --------------------------------------------------
    # Main Entry
    # --------------------------------------------------

    def run(self):

        logging.info("Marking all previous files as missing (pre-scan stage)")
        self.db.mark_all_files_missing(self.drive_id)

        for root, dirs, files in os.walk(self.drive_root):

            for file_name in files:

                full_path = os.path.join(root, file_name)

                if not os.path.isfile(full_path):
                    continue

                self.total_files += 1

                try:
                    self._process_file(full_path, file_name)

                except Exception as e:
                    logging.error(f"File processing failed: {full_path} | {e}")

        logging.info("Scan completed. Finalizing active files.")
        self.db.finalize_missing_files(self.drive_id)

        self._print_summary()

    # --------------------------------------------------
    # File Processing
    # --------------------------------------------------

    def _process_file(self, full_path, file_name):

        relative_path = os.path.relpath(full_path, self.drive_root)
        relative_path = relative_path.replace("\\", "/")

        stat = os.stat(full_path)

        size_bytes = stat.st_size
        created_fs = datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified_fs = datetime.fromtimestamp(stat.st_mtime).isoformat()

        header_valid = 1
        sha256 = None

        if is_valid_audio(full_path):
            self.audio_files += 1

            header_valid = 1

            sha256 = compute_sha256(full_path, self.test_mode)

        else:
            header_valid = 0

        file_id = self.db.upsert_file(
            drive_id=self.drive_id,
            relative_path=relative_path,
            file_name=file_name,
            extension=os.path.splitext(file_name)[1].lower(),
            size_bytes=size_bytes,
            created_fs=created_fs,
            modified_fs=modified_fs,
            header_valid=header_valid,
            sha256=sha256
        )

        self.db.insert_path_components(file_id, relative_path)

        # Extract metadata only for valid audio
        if header_valid and self.extract_metadata:
            metadata = extract_audio_metadata(full_path)
            if metadata:
                self.db.upsert_audio_metadata(file_id, metadata)

        self.total_bytes += size_bytes

        if self.total_files % 100 == 0:
            logging.info(f"Processed {self.total_files} files...")

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    def _print_summary(self):

        logging.info("========== SCAN SUMMARY ==========")
        logging.info(f"Total files scanned : {self.total_files}")
        logging.info(f"Audio files found   : {self.audio_files}")
        logging.info(f"Total size scanned  : {human_readable_size(self.total_bytes)}")
        logging.info("==================================")

# ===========================>

# ---------------------------------------------------------------------------------------------------
# utils.py=================>
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

# ===========================>

