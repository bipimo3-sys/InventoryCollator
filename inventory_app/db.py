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
