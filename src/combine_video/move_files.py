import logging
import os
from pathlib import Path
import shutil
import os
import platform
import logging
from typing import Optional, Dict


def move_all_files_in_folder(
    input_folder: Path, output_folder: Path, extensions: list[str] = [".mp4", ".lrf"]
) -> None:
    """
    Moves all files from the input folder to the output folder, renaming files
    in the destination if conflicts occur while preserving original files.

    Args:
        input_folder: Source directory containing files to move
        output_folder: Target directory for moved files
    """
    logging.info(f"Moving files from {input_folder} to {output_folder}")
    # Create output directory if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)

    # Get all files in input directory (excluding directories)
    files_to_move: list[Path] = []

    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(tuple(extensions)):
                src_path = Path(root) / file
                files_to_move.append(src_path)

    for src_path in files_to_move:
        # Skip the output folder if it's inside input folder
        if src_path == output_folder:
            continue

        # Create destination path and handle name conflicts
        dest_path = output_folder / src_path.name
        conflict_number = 0

        # Find first available filename
        while dest_path.exists():
            conflict_number += 1
            stem = src_path.stem
            suffix = src_path.suffix
            dest_path = output_folder / f"{stem}_{conflict_number}{suffix}"

        # Perform the move
        shutil.move(str(src_path), str(dest_path))
        logging.info(
            f"Moved '{src_path.name}' to '{dest_path.relative_to(output_folder.parent)}'"
        )
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
    elif platform.system() == "Darwin":
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
            logging.error("Linux mount point detection failed - /proc/mounts not found.")
    return None


def find_dji_action4_drive() -> Optional[str]:
    """Finds the drive letter of a DJI Action 4 device."""
    if platform.system() == "Windows":
        for drive in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = f"{drive}:\\"
            if os.path.exists(drive_path) and os.path.exists(os.path.join(drive_path, "DCIM", "DJI_001")):
                logging.info(f"DJI Action 4 drive found: {drive_path}")
                return drive_path
    elif platform.system() == "Darwin":
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
            logging.error("Linux mount point detection failed - /proc/mounts not found.")
    return None

if __name__ == "__main__":
    fly6pro_drive = find_fly6pro_drive()
    dji_action4_drive = find_dji_action4_drive()
    MAIN_FOLDER = Path("C:/Video/Input")
    if fly6pro_drive:
        move_all_files_in_folder(fly6pro_drive, MAIN_FOLDER / "FLY6PRO")
    if dji_action4_drive:
        move_all_files_in_folder(dji_action4_drive, MAIN_FOLDER / "DJI_ACTION4")

