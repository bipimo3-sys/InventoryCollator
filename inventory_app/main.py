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
