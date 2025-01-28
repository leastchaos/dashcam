import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import subprocess
import json
from typing import List, Optional

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# Supported video file extensions (add more as needed)
SUPPORTED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".mts", ".m2ts"]


def get_video_recording_time(video_file: Path) -> str:
    """
    Extract the recording time from the video file using filename, metadata, or modification time.
    Returns a datetime string in the format "%Y%m%d_%H%M%S" adjusted to UTC+8.
    """

    # First, try to get metadata using ffprobe
    try:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format_tags=creation_time",
            "-of",
            "json",
            str(video_file),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)

        creation_time = metadata.get("format", {}).get("tags", {}).get("creation_time")
        if creation_time:
            # Parse the creation_time into a datetime object
            try:
                dt = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                dt = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%SZ")
            
            # Make the datetime timezone-aware in UTC
            dt_utc = dt.replace(tzinfo=timezone.utc)
            # Convert to UTC+8
            utc_plus_8 = timezone(timedelta(hours=8))
            dt_utc8 = dt_utc.astimezone(utc_plus_8)
            
            logging.info(f"Using metadata creation time (UTC+8) for {video_file.name}: {dt_utc8}")
            return dt_utc8.strftime("%Y%m%d_%H%M%S")

    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError, ValueError) as e:
        logging.warning(f"Metadata extraction failed for {video_file.name}: {e}")

    # Fallback: Try to extract datetime from filename
    filename_stem = video_file.stem
    datetime_str = extract_datetime_from_filename(filename_stem)
    if datetime_str:
        return datetime_str

    # If all else fails, use modification time (not implemented here)
    raise ValueError(f"No valid recording time found for {video_file.name}")


def extract_datetime_from_filename(filename_stem: str) -> Optional[str]:
    """
    Try to extract a datetime from the filename if it starts with 14 digits (YYYYMMDDHHMMSS).
    Returns formatted datetime string if valid, otherwise None.
    """
    match = re.match(r"^(\d{14})", filename_stem)
    if match:
        datetime_str = match.group(1)
        try:
            dt = datetime.strptime(datetime_str, "%Y%m%d%H%M%S")
            logging.info(f"Using datetime from filename: {filename_stem}")
            return dt.strftime("%Y%m%d_%H%M%S")
        except ValueError as e:
            logging.warning(f"Invalid datetime in filename {filename_stem}: {e}")
    return None


def get_first_video_file(
    folder: Path, extensions: List[str] = SUPPORTED_EXTENSIONS
) -> Path:
    """Get the first video file in the folder sorted by name"""
    for ext in extensions:
        video_files = sorted(folder.glob(f"*{ext}"))
        if video_files:
            return video_files[0]
    raise FileNotFoundError(f"No video files found in folder: {folder}")


def get_first_video_recording_time(folder: Path) -> str:
    """Get recording time from first video file in folder"""
    try:
        video_file = get_first_video_file(folder)
        return get_video_recording_time(video_file)
    except Exception as e:
        logging.error(f"Error processing folder {folder}: {e}")
        raise


if __name__ == "__main__":
    try:
        folder = Path("C:/Video/Input/Test")
        recording_time = get_first_video_recording_time(folder)
        print(f"Recording time: {recording_time}")
    except Exception as e:
        logging.error(f"Main execution failed: {e}")