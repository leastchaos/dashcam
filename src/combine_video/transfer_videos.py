import os
from pathlib import Path
import shutil
import platform
import logging
from typing import Optional, List


def find_fly6pro_drive() -> Optional[str]:
    """Finds the drive letter of the FLY6PRO device."""
    if platform.system() == "Windows":
        for drive in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            try:
                if os.path.exists(f"{drive}:\\"):
                    if "FLY6PRO" in os.popen(f"vol {drive}:").read().upper():
                        logging.info(f"FLY6PRO drive found: {drive}:\\")
                        return f"{drive}:\\"
            except OSError as e:
                logging.warning(f"Error accessing drive {drive}: {e}")
    elif platform.system() == "Darwin":  # macOS
        for volume in os.listdir("/Volumes"):
            if "FLY6PRO" in volume.upper():
                logging.info(f"FLY6PRO volume found: /Volumes/{volume}")
                return os.path.join("/Volumes", volume)
    elif platform.system() == "Linux":
        try:
            with open("/proc/mounts", "r") as f:
                mounts = f.readlines()
            for mount in mounts:
                if "FLY6PRO" in mount.upper():
                    mount_point = mount.split(" ")[1]
                    logging.info(f"FLY6PRO mount point found: {mount_point}")
                    return mount_point
        except FileNotFoundError:
            logging.error(
                "Error: /proc/mounts not found. Linux mount point detection may not work."
            )

    logging.warning("FLY6PRO drive not found.")
    return None


def find_dji_action4_drive() -> Optional[str]:
    """Finds the drive letter of a DJI Action 4 device."""
    if platform.system() == "Windows":
        for drive in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            try:
                drive_path = f"{drive}:\\"
                if os.path.exists(drive_path) and os.path.exists(
                    os.path.join(drive_path, "DCIM", "DJI_001")
                ):
                    logging.info(f"DJI Action 4 drive found: {drive_path}")
                    return drive_path
            except OSError as e:
                logging.warning(f"Error accessing drive {drive}: {e}")
    elif platform.system() == "Darwin":  # macOS
        for volume in os.listdir("/Volumes"):
            volume_path = os.path.join("/Volumes", volume)
            if os.path.exists(os.path.join(volume_path, "DCIM", "DJI_001")):
                logging.info(f"DJI Action 4 volume found: {volume_path}")
                return volume_path
    elif platform.system() == "Linux":
        try:
            with open("/proc/mounts", "r") as f:
                mounts = f.readlines()
            for mount in mounts:
                mount_point = mount.split(" ")[1]
                if os.path.exists(os.path.join(mount_point, "DCIM", "DJI_001")):
                    logging.info(f"DJI Action 4 mount point found: {mount_point}")
                    return mount_point
        except FileNotFoundError:
            logging.error(
                "Error: /proc/mounts not found. Linux mount point detection may not work."
            )

    logging.warning("DJI Action 4 drive not found.")
    return None


def transfer_videos(
    source_drive: Optional[str], destination_folder: str, delete_after: bool = False
) -> None:
    """Transfers video files from the specified drive to the destination folder."""
    if not source_drive:
        logging.warning("Source drive not provided, skipping transfer.")
        return

    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
        logging.info(f"Created destination folder: {destination_folder}")

    video_extensions = (".mp4", ".avi", ".mov", ".3gp")  # Add more if needed
    transferred_files = []  # store files for deletion
    for root, _, files in os.walk(source_drive):
        for file in files:
            if file.lower().endswith(video_extensions):
                source_path = os.path.join(root, file)
                destination_path = os.path.join(destination_folder, file)
                try:
                    shutil.copy2(source_path, destination_path)
                    logging.info(f"Copied: {file}")
                    transferred_files.append(source_path)
                except Exception as e:
                    logging.error(f"Error copying {file}: {e}")

    if delete_after:
        for file_path in transferred_files:
            try:
                os.remove(file_path)
                logging.info(f"Deleted: {os.path.basename(file_path)}")
            except Exception as e:
                logging.error(f"Error deleting {file_path}: {e}")


def transfer(
        delete_after_transfer: bool = True,
        action4_destination_folder: Path = Path("C:\\Video\\Input\\OA4"),
        fly6pro_destination_folder: Path = Path("C:\\Video\\Input\\Fly6Pro"), 
    ) -> dict[str, Path]:
    """Main function to execute the script."""
    action4_drive = find_dji_action4_drive()
    fly6pro_drive = find_fly6pro_drive()
    if action4_drive:
        action4_destination = os.path.join(action4_destination_folder, "DJI_Action4")
        transfer_videos(action4_drive, action4_destination, delete_after_transfer)
        logging.info("DJI Action 4 video transfer complete.")

    if fly6pro_drive:
        fly6pro_destination = os.path.join(fly6pro_destination_folder, "Fly6Pro")
        transfer_videos(fly6pro_drive, fly6pro_destination, delete_after_transfer)
        logging.info("FLY6PRO video transfer complete.")

    if not action4_drive and not fly6pro_drive:
        logging.warning(
            "No supported device found. Please connect the device(s) and try again."
        )

    return {
        "DJI_Action4": Path(action4_destination) if action4_drive else None,
        "Fly6Pro": Path(fly6pro_destination) if fly6pro_drive else None,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transfer()
