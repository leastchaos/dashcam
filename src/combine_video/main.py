import logging
from datetime import datetime
from pathlib import Path
from typing import Literal
from combine_clips import combine_clips
from get_video_recording_time import get_first_video_recording_time
from upload_video import upload_video
from move_files import move_all_files_in_folder

MAIN_VIDEO_FOLDER = Path("C:/Video/")
INPUT_VIDEO_FOLDER_PATH = MAIN_VIDEO_FOLDER / "Input"
OUTPUT_VIDEO_FOLDER_PATH = MAIN_VIDEO_FOLDER / "Output"
ARCHIVE_VIDEO_FOLDER_PATH = MAIN_VIDEO_FOLDER / "Archive"
UPLOADED_VIDEO_FOLDER_PATH = MAIN_VIDEO_FOLDER / "Uploaded"

def main(
        tags: list[str],
        category_id: int,
        privacy_status: Literal["public", "private", "unlisted"] = "private",
        max_upload_retries: int = 3
):
    input_folders = [
        INPUT_VIDEO_FOLDER_PATH / folder
        for folder in INPUT_VIDEO_FOLDER_PATH.iterdir()
        if folder.is_dir()
    ]

    for folder in input_folders:
        # if folder is empty, skip
        if len(list(folder.iterdir())) == 0:
            logging.info(f"Folder {folder} is empty. Skipping...")
            continue
        
        video_datetime = get_first_video_recording_time(folder)
        logging.info(f"video_datetime: {video_datetime}")
        # create output folder
        output_filename = video_datetime + "_" + folder.name
        output_file_path = OUTPUT_VIDEO_FOLDER_PATH / (output_filename + ".mp4")

        # combine clips
        try:
            combine_clips(folder, output_file_path)
        except FileExistsError:
            logging.warning(f"Output file already exists: {output_file_path}")
            # check if want to delete it and combine clips or continue with existing file
            user_input = input(
                f"Output file already exists: {output_file_path}. Do you want to delete it and combine clips? (y/n): "
            )
            if user_input.lower() == "y":
                output_file_path.unlink()
                combine_clips(folder, output_file_path)
            else:
                logging.info(
                    "Skipping combining file and continuing with existing video."
                )
        archive_path = ARCHIVE_VIDEO_FOLDER_PATH / output_filename
        move_all_files_in_folder(folder, archive_path)
        logging.info(f"Files moved to {archive_path}")
        # upload video
        video_id = upload_video(
            file_path=output_file_path,
            title=output_filename,
            description=video_datetime.split("_")[0],
            tags=tags,
            category_id=category_id,  # Sports category
            privacy_status=privacy_status,
            max_retries=max_upload_retries,
        )

        if not video_id:
            logging.error("Video upload failed.")
            continue
            # move files to uploaded
        uploaded_path = UPLOADED_VIDEO_FOLDER_PATH / output_filename
        move_all_files_in_folder(output_file_path.parent, uploaded_path)
        logging.info(f"Video uploaded with ID: {video_id}")
        logging.info(f"Files moved to {uploaded_path}")
            
    # check for unuploaded videos
    for file in OUTPUT_VIDEO_FOLDER_PATH.iterdir():
        if file.is_file():
            logging.warning(f"Video file not uploaded: {file}")
            # upload video
            video_id = upload_video(
                file_path=output_file_path,
                title=output_filename,
                description=video_datetime.split("_")[0],
                tags=tags,
                category_id=category_id,  # Sports category
                privacy_status=privacy_status,
                max_retries=max_upload_retries,
            )

            if not video_id:
                logging.error("Video upload failed.")
                return
                # move files to uploaded
            uploaded_path = UPLOADED_VIDEO_FOLDER_PATH / output_filename
            move_all_files_in_folder(output_file_path.parent, uploaded_path)
            logging.info(f"Video uploaded with ID: {video_id}")
            logging.info(f"Files moved to {uploaded_path}")

# Main function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main(
        tags=["test"],
        category_id=17,
        privacy_status="private",
        max_upload_retries=3
    )
