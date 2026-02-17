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
