import json
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Any, Optional

import requests
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
)
from garth.exc import GarthHTTPError
from enum import Enum

# --- Configuration ---
SECRETS_JSON = Path("./secrets/garmin_secret.json")
TOKENSTORE = Path("./cache/.garminconnect")
TOKENSTORE_BASE64 = Path("./cache/.garminconnect_base64")

# Initialize logger
logger = logging.getLogger(__name__)

# Load credentials from secrets file
secrets = json.loads(SECRETS_JSON.read_text())
GARMIN_CONNECT_EMAIL = secrets["username"]
GARMIN_CONNECT_PASSWORD = secrets["password"]


def get_mfa() -> str:
    """Get Multi-Factor Authentication code from user input."""
    logger.info("Prompting user for MFA code")
    return input("MFA one-time code: ")


def display_json(api_call: str, output: Any) -> None:
    """Format API output for better readability."""
    dashed = "-" * 20
    header = f"{dashed} {api_call} {dashed}"
    footer = "-" * len(header)

    logger.debug(header)
    logger.debug(
        json.dumps(output, indent=4) if isinstance(output, (dict, list)) else output
    )
    logger.debug(footer)


def get_garmin_client(email: str, password: str) -> Optional[Garmin]:
    """Initialize and authenticate Garmin API client."""
    token_store_path = TOKENSTORE.expanduser()
    try:
        logger.info(
            f"Attempting to authenticate using existing token store at {token_store_path}"
        )
        garmin = Garmin()
        garmin.login(str(token_store_path))
        logger.info("Successfully authenticated using stored tokens")
        return garmin

    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError) as e:
        logger.warning(f"Token authentication failed: {str(e)}")
        logger.info("Attempting fresh login with credentials...")

        try:
            garmin = Garmin(
                email=email, password=password, is_cn=False, prompt_mfa=get_mfa
            )
            garmin.login()
            logger.info("Successfully authenticated with credentials")
            _save_garmin_tokens(
                garmin, token_store_path, TOKENSTORE_BASE64.expanduser()
            )
            return garmin

        except (
            GarminConnectAuthenticationError,
            requests.exceptions.RequestException,
        ) as err:
            logger.error(f"Authentication failed: {err}")
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
        return None


def _save_garmin_tokens(
    garmin: Garmin, token_store_path: Path, token_base64_path: Path
) -> None:
    """Save Garmin authentication tokens."""
    garmin.garth.dump(str(token_store_path))

    token_base64 = garmin.garth.dumps()
    token_base64_path.parent.mkdir(parents=True, exist_ok=True)
    token_base64_path.write_text(token_base64)

    logger.info(
        f"Tokens successfully saved to:\n- {token_store_path}\n- {token_base64_path}"
    )


class ActivityFormat(Enum):
    FIT = "FIT"
    GPX = "GPX"


def download_latest_activity(
    output_folder: Optional[Path] = None,
    output_filename: str = None,
    start_index: int = 0,
    format: ActivityFormat = ActivityFormat.FIT,
) -> bytes:
    """Download activity from Garmin Connect."""

    logger.info(
        f"Starting download process for activity index {start_index} in {format.value} format"
    )
    client = get_garmin_client(GARMIN_CONNECT_EMAIL, GARMIN_CONNECT_PASSWORD)
    output_folder = output_folder or Path.cwd()

    if not client:
        logger.error("Failed to initialize Garmin client")
        raise ConnectionError("Failed to authenticate Garmin client")

    try:
        activities = client.get_activities(start_index, 1)
        if not activities:
            logger.error(f"No activities found at index {start_index}")
            raise ValueError(f"No activities found at index {start_index}")

        activity_id = activities[0]["activityId"]
        logger.info(f"Found activity ID: {activity_id}")

        if not output_filename:
            output_filename = str(activity_id)

        output_filepath = Path(
            output_folder, f"{output_filename}.{format.value.lower()}"
        )

        if format == ActivityFormat.FIT:
            return _download_fit_activity(client, activity_id, output_filepath)
        elif format == ActivityFormat.GPX:
            return _download_gpx_activity(client, activity_id, output_filepath)
        else:
            # This should never happen now, but keep it for robustness
            logger.error(f"Unsupported format: {format}")
            raise ValueError(f"Unsupported format: {format}")

    except (ConnectionError, ValueError, FileNotFoundError) as e:
        logger.error(f"Failed to download activity: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during download: {str(e)}")
        raise


def _download_fit_activity(client, activity_id, output_filepath: Path) -> bytes:
    """Download, extract, and save a FIT activity."""
    zip_path = Path(f"{activity_id}.zip")
    extract_dir = Path(f"{activity_id}")
    fit_data = None  # Initialize fit_data outside of the try block

    try:
        logger.info(f"Downloading activity {activity_id} in ORIGINAL (FIT) format")
        fit_data = client.download_activity(
            activity_id, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL
        )

        zip_path.write_bytes(fit_data)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        fit_file = extract_dir / f"{activity_id}_ACTIVITY.fit"
        if not fit_file.exists():
            raise FileNotFoundError(
                f"FIT file not found in extracted contents: {fit_file}"
            )

        shutil.move(str(fit_file), str(output_filepath))
        logger.info(f"Successfully saved activity to {output_filepath.resolve()}")

        return fit_data

    finally:
        zip_path.unlink(missing_ok=True)
        shutil.rmtree(extract_dir, ignore_errors=True)


def _download_gpx_activity(client, activity_id, output_filepath: Path) -> bytes:
    """Download and save a GPX activity."""
    logger.info(f"Downloading activity {activity_id} in GPX format")
    gpx_data = client.download_activity(
        activity_id, dl_fmt=Garmin.ActivityDownloadFormat.GPX
    )

    output_filepath.write_bytes(gpx_data)
    logger.info(f"Successfully saved GPX file to {output_filepath.resolve()}")

    return gpx_data


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("garmin_export.log")],
    )
    try:
        # Example: Download the latest activity in GPX format
        download_latest_activity(format=ActivityFormat.FIT, start_index=0)
    except Exception as e:
        logger.critical(f"Fatal error in main execution: {str(e)}", exc_info=True)
        raise
