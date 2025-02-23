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
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from garth.exc import GarthHTTPError

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
    logger.debug(json.dumps(output, indent=4) if isinstance(output, (dict, list)) else output)
    logger.debug(footer)


def get_garmin_client(email: str, password: str) -> Optional[Garmin]:
    """Initialize and authenticate Garmin API client."""
    try:
        logger.info(f"Attempting to authenticate using existing token store at {TOKENSTORE}")
        garmin = Garmin()
        garmin.login(str(TOKENSTORE))
        logger.info("Successfully authenticated using stored tokens")
        return garmin

    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError) as e:
        logger.warning(f"Token authentication failed: {str(e)}")
        logger.info("Attempting fresh login with credentials...")

        try:
            garmin = Garmin(
                email=email, 
                password=password, 
                is_cn=False, 
                prompt_mfa=get_mfa
            )
            garmin.login()
            logger.info("Successfully authenticated with credentials")
            
            # Save tokens using both methods
            token_store_path = TOKENSTORE.expanduser()
            garmin.garth.dump(str(token_store_path))
            
            token_base64 = garmin.garth.dumps()
            token_base64_path = TOKENSTORE_BASE64.expanduser()
            token_base64_path.parent.mkdir(parents=True, exist_ok=True)
            token_base64_path.write_text(token_base64)
            
            logger.info(f"Tokens successfully saved to:\n- {token_store_path}\n- {token_base64_path}")
            return garmin

        except (GarminConnectAuthenticationError, requests.exceptions.HTTPError) as err:
            logger.error("Authentication failed: %s", err)
        except Exception as e:
            logger.error("Unexpected error during authentication: %s", str(e))
        
        return None


def download_latest_activity(output_filename: Optional[str] = None, start_index: int = 0, format: str = "FIT") -> bytes:
    """
    Download activity from Garmin Connect.
    
    Args:
        output_filepath: Path to save the downloaded file
        start_index: Index of activity to download (0 = most recent)
        format: Format to download ("FIT" or "GPX")
    """
    logger.info(f"Starting download process for activity index {start_index} in {format} format")
    
    client = get_garmin_client(GARMIN_CONNECT_EMAIL, GARMIN_CONNECT_PASSWORD)
    if not client:
        logger.error("Failed to initialize Garmin client")
        raise ConnectionError("Failed to authenticate Garmin client")

    try:
        logger.info(f"Fetching activities starting from index {start_index}")
        activities = client.get_activities(start_index, 1)
        if not activities:
            logger.error("No activities found at index %s", start_index)
            raise ValueError(f"No activities found at index {start_index}")
            
        activity_id = activities[0]["activityId"]
        logger.info(f"Found activity ID: {activity_id}")

        if not output_filename:
            output_filename = f"{activity_id}.{format.lower()}"

        if format.upper() == "FIT":
            output_filepath = Path(f"{output_filename}.fit")
            logger.info(f"Downloading activity {activity_id} in ORIGINAL (FIT) format")
            fit_data = client.download_activity(
                activity_id, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL
            )

            zip_path = Path(f"{activity_id}.zip")
            logger.debug(f"Writing zip file to {zip_path.resolve()}")
            zip_path.write_bytes(fit_data)

            extract_dir = Path(f"{activity_id}")
            logger.info(f"Extracting zip contents to {extract_dir.resolve()}")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
                logger.debug(f"Extracted files: {zip_ref.namelist()}")
            
            logger.debug(f"Removing zip file {zip_path}")
            zip_path.unlink()

            fit_file = extract_dir / f"{activity_id}_ACTIVITY.fit"
            if not fit_file.exists():
                logger.error(f"Expected FIT file not found: {fit_file}")
                raise FileNotFoundError(f"FIT file not found in extracted contents: {fit_file}")

            logger.info(f"Moving FIT file to {output_filepath.resolve()}")
            shutil.move(str(fit_file), str(output_filepath))
            logger.info(f"Successfully saved activity to {output_filepath}")

            logger.debug(f"Cleaning up extraction directory {extract_dir}")
            shutil.rmtree(extract_dir)
            logger.debug("Cleanup complete")

            return fit_data

        elif format.upper() == "GPX":
            output_filepath = Path(f"{output_filename}.gpx")
            logger.info(f"Downloading activity {activity_id} in GPX format")
            gpx_data = client.download_activity(
                activity_id, dl_fmt=Garmin.ActivityDownloadFormat.GPX
            )

            logger.info(f"Writing GPX file to {output_filepath.resolve()}")
            output_filename.write_bytes(gpx_data)
            logger.info(f"Successfully saved GPX file to {output_filepath}")

            return gpx_data

        else:
            logger.error(f"Unsupported format: {format}")
            raise ValueError(f"Unsupported format: {format}")

    except Exception as e:
        logger.error(f"Failed to download activity: {str(e)}")
        # Cleanup temporary files if they exist
        if "zip_path" in locals() and zip_path.exists():
            logger.warning(f"Removing temporary zip file {zip_path}")
            zip_path.unlink(missing_ok=True)
        if "extract_dir" in locals() and extract_dir.exists():
            logger.warning(f"Removing temporary directory {extract_dir}")
            shutil.rmtree(extract_dir, ignore_errors=True)
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("garmin_export.log")
        ]
    )
    try:
        # Example: Download the latest activity in GPX format
        download_latest_activity(Path("activity.gpx"), format="GPX", start_index=1)
    except Exception as e:
        logger.critical(f"Fatal error in main execution: {str(e)}", exc_info=True)
        raise