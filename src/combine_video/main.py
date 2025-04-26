import asyncio
import logging
from datetime import datetime
from pathlib import Path
import shutil
from typing import Literal

from combine_clips import combine_clips
from get_video_recording_time import get_first_video_recording_time
from upload_video import upload_video
from move_files import find_dji_action4_drive, find_fly6pro_drive, move_all_files_in_folder

MAIN_VIDEO_FOLDER = Path("C:/Video/")
INPUT_VIDEO_FOLDER_PATH = MAIN_VIDEO_FOLDER / "Input"
OUTPUT_VIDEO_FOLDER_PATH = MAIN_VIDEO_FOLDER / "Output"
ARCHIVE_VIDEO_FOLDER_PATH = MAIN_VIDEO_FOLDER / "Archive"
UPLOADED_VIDEO_FOLDER_PATH = MAIN_VIDEO_FOLDER / "Uploaded"


async def upload_and_move(
    file_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category_id: int,
    privacy_status: Literal["public", "private", "unlisted"],
    max_upload_retries: int,
):
    """Uploads a video and moves it to the uploaded folder (async)."""
    video_id = await upload_video(
        file_path=file_path,
        title=title,
        description=description,
        tags=tags,
        category_id=category_id,
        privacy_status=privacy_status,
        max_retries=max_upload_retries,
    )

    if not video_id:
        logging.error(f"Video upload failed for {file_path}.")
        return False

    uploaded_path = UPLOADED_VIDEO_FOLDER_PATH / file_path.name

    logging.info(f"Video uploaded with ID: {video_id}")
    # move uploaded file to uploaded folder
    shutil.move(file_path, uploaded_path)
    logging.info(f"Files moved to {uploaded_path}")
    return True


def process_folder(
    folder: Path,
):
    """Processes a single input folder."""
    if not any(folder.iterdir()):
        logging.info(f"Folder {folder} is empty. Skipping...")
        return

    video_datetime = get_first_video_recording_time(folder)
    logging.info(f"video_datetime: {video_datetime}")

    output_filename = video_datetime + "_" + folder.name
    output_file_path = OUTPUT_VIDEO_FOLDER_PATH / (output_filename + ".mp4")

    try:
        combine_clips(folder, output_file_path)
    except FileExistsError:
        logging.warning(f"Output file already exists: {output_file_path}")
        user_input = input(
            f"Output file already exists: {output_file_path}. Do you want to delete it and combine clips? (y/n): "
        )
        if user_input.lower() == "y":
            output_file_path.unlink()
            combine_clips(folder, output_file_path)
        else:
            logging.info("Skipping combining file and continuing with existing video.")

    archive_path = ARCHIVE_VIDEO_FOLDER_PATH / output_filename
    move_all_files_in_folder(folder, archive_path)
    logging.info(f"Files moved to {archive_path}")

    return output_file_path, output_filename, video_datetime


async def check_unuploaded_videos(
    tags: list[str],
    category_id: int,
    privacy_status: Literal["public", "private", "unlisted"],
    max_upload_retries: int,
):
    """Checks for and uploads any remaining videos in the output folder."""
    upload_tasks = []
    for file in OUTPUT_VIDEO_FOLDER_PATH.iterdir():
        if file.is_file():
            logging.warning(f"Video file not uploaded: {file}")
            video_datetime = file.stem.split("_")[0]
            upload_tasks.append(
                upload_and_move(
                    file,
                    file.stem,
                    video_datetime,
                    tags,
                    category_id,
                    privacy_status,
                    max_upload_retries,
                )
            )
    await asyncio.gather(*upload_tasks)


async def main(
    tags: list[str],
    category_id: int,
    privacy_status: Literal["public", "private", "unlisted"] = "private",
    max_upload_retries: int = 3,
):
    """Main function to process video folders."""
    input_folders = [
        folder for folder in INPUT_VIDEO_FOLDER_PATH.iterdir() if folder.is_dir()
    ]

    upload_tasks = []
    for folder in input_folders:
        result = process_folder(folder)
        if result:
            output_file_path, output_filename, video_datetime = result
            upload_tasks.append(
                upload_and_move(
                    output_file_path,
                    output_filename,
                    video_datetime.split("_")[0],
                    tags,
                    category_id,
                    privacy_status,
                    max_upload_retries,
                )
            )

    await asyncio.gather(*upload_tasks)
    await check_unuploaded_videos(tags, category_id, privacy_status, max_upload_retries)

async def initialize_drives():
    """Concurrently move files from detected drives to input folders."""
    fly6pro_drive = find_fly6pro_drive()
    dji_action4_drive = find_dji_action4_drive()
    
    tasks = []
    if fly6pro_drive:
        tasks.append(
            asyncio.to_thread(
                move_all_files_in_folder,
                fly6pro_drive,
                INPUT_VIDEO_FOLDER_PATH / "FLY6PRO"
            )
        )
    if dji_action4_drive:
        tasks.append(
            asyncio.to_thread(
                move_all_files_in_folder,
                dji_action4_drive,
                INPUT_VIDEO_FOLDER_PATH / "DJI_ACTION4"
            )
        )
    await asyncio.gather(*tasks)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Run initialization and main sequentially in the event loop
    asyncio.run(initialize_drives())
    asyncio.run(
        main(
            tags=["cycling", "ride", "singapore"],
            category_id=17,
            privacy_status="private",
            max_upload_retries=3,
        )
    )
