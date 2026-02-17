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
