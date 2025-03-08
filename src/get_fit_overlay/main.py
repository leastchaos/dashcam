import logging
import os
from pathlib import Path
from download_fit_file import download_latest_activity
from dashboard import generate_dashboard

MAIN_VIDEO_FOLDER = Path("C:/Video/")
FIT_FOLDER = MAIN_VIDEO_FOLDER / "FIT"
OVERLAY_FOLDER = MAIN_VIDEO_FOLDER / "Overlay"
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path.cwd() / "logs/garmin_export.log"),
        ],
    )
    os.makedirs(FIT_FOLDER, exist_ok=True)
    os.makedirs(OVERLAY_FOLDER, exist_ok=True)
    latest_fit_file = download_latest_activity(output_folder=FIT_FOLDER, start_index=31)
    output_overlay_file = OVERLAY_FOLDER / latest_fit_file.with_suffix(".mp4")
    generate_dashboard(
        fit=latest_fit_file,
        output=output_overlay_file,
        font="verdana",
        overlay_size="1920x1080",
        layout_xml=Path(r"C:\Python Projects\dashcam\power-1920x1080.xml"),
    )
    logging.info(f"Video exported to {output_overlay_file}")
