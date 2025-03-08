import asyncio
from pathlib import Path
import ssl
from typing import Literal
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import logging
from tqdm import tqdm
import os

# Configuration setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SECRETS_DIR = PROJECT_ROOT / "secrets"
CLIENT_SECRETS_FILE = SECRETS_DIR / "client_secret.json"
TOKEN_FILE = SECRETS_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Validate secrets directory
if not SECRETS_DIR.exists():
    raise FileNotFoundError(f"Secrets directory not found: {SECRETS_DIR}")


def get_authenticated_service() -> build:
    """Authenticates and returns YouTube API service instance."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


async def upload_video(
    file_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category_id: int,
    privacy_status: Literal["public", "private", "unlisted"] = "private",
    max_retries: int = 3,
) -> str | None:
    """
    Uploads a video to YouTube with resumable support, progress tracking, and async.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Video file not found: {file_path}")

    try:
        youtube = get_authenticated_service()
    except Exception as e:
        if "invalid_grant" in str(e):
            logging.error("Token expired or revoked. Deleting token and retrying.")
            if TOKEN_FILE.exists():
                os.remove(TOKEN_FILE)
            try:
                youtube = get_authenticated_service()  # try again after deleting token.
            except Exception as retry_e:
                logging.error(
                    f"Failed to re-authenticate after token deletion: {retry_e}"
                )
                return None
        else:
            logging.error(f"Authentication error: {e}")
            return None

    request_body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": [tag[:500] for tag in tags],
            "categoryId": str(category_id),
        },
        "status": {"privacyStatus": privacy_status},
    }

    media = MediaFileUpload(
        str(file_path), mimetype="video/*", chunksize=5 * 1024 * 1024, resumable=True
    )

    try:
        request = youtube.videos().insert(
            part="snippet,status", body=request_body, media_body=media
        )

        with tqdm(total=100, desc=f"Uploading {title}", unit="%") as pbar:
            retry_count = 0
            previous_percent = 0
            response = None

            while response is None:
                try:
                    status, response = await asyncio.to_thread(request.next_chunk)
                    if status:
                        current = int(status.progress() * 100)
                        pbar.update(current - previous_percent)
                        previous_percent = current
                    retry_count = 0

                except HttpError as e:
                    if (
                        e.resp.status in [500, 502, 503, 504]
                        and retry_count < max_retries
                    ):
                        retry_count += 1
                        logging.warning(
                            f"Server error ({e}), retry {retry_count}/{max_retries}"
                        )
                        continue
                    raise
                except ssl.SSLEOFError as e: #Add this block.
                    retry_count += 1
                    if retry_count <= max_retries:
                        logging.warning(f"SSL Error (retry {retry_count}/{max_retries}): {e}")
                        await asyncio.sleep(2**retry_count) #exponential backoff.
                        continue
                    else:
                        logging.error(f"SSL Error: Max retries exceeded. Upload failed. {e}")
                        return None

        if previous_percent < 100:
            pbar.update(100 - previous_percent)

        video_id = response.get("id")
        print(f"\nUpload complete! Video ID: {video_id}")
        return video_id

    except HttpError as e:
        print(f"Upload failed: {e}")
        return None


if __name__ == "__main__":
    # Example usage with parameter validation
    try:
        video_path = Path(r"C:\Python Projects\dashcam\test.mp4")
        asyncio.run(
            upload_video(
                file_path=video_path,
                title="TEst",
                description="Test",
                tags=["test"],
                category_id=17,
                privacy_status="private",
            )
        )
    except Exception as e:
        print(f"Fatal error: {e}")
