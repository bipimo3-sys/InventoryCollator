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
