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
