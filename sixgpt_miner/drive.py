import typing as T
import os
import click
import requests
import json
import datetime as dt
import io
from uuid import uuid4
from constants import BASE_NAME

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

from constants import TMP_DRIVE_AUTH, API_URL

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_active_account() -> T.Optional[Credentials]:
    if os.path.exists(TMP_DRIVE_AUTH):
        with open(TMP_DRIVE_AUTH, "r") as token:
            code = json.load(token)
            code["expiry"] = dt.datetime.fromisoformat(code["expiry"][:-1]).replace(
                tzinfo=None
            )
            creds = Credentials(**code)
        if creds.expired:
            creds = _call_sixgpt_api_server_refresh(creds)
            if creds is not None:
                _persist_credentials(creds)
            return creds
        if creds.valid:
            return creds
    return None


def set_active_account() -> T.Optional[Credentials]:
    if os.path.exists(TMP_DRIVE_AUTH):
        os.remove(TMP_DRIVE_AUTH)
        click.echo("Removed existing active account.")
    click.echo("Setting active account...")
    creds = _call_sixgpt_api_server()
    if not creds:
        click.echo("Failed to get the drive auth code from sixgpt's auth server.")
        return
    _persist_credentials(creds)
    click.echo("Active account set.")
    return creds


def remove_active_account() -> None:
    click.echo("Removing active account...")
    if os.path.exists(TMP_DRIVE_AUTH):
        os.remove(TMP_DRIVE_AUTH)
        click.echo("Active account removed.")
    else:
        click.echo("No active account found.")


def _persist_credentials(creds: Credentials) -> None:
    os.makedirs(os.path.dirname(TMP_DRIVE_AUTH), exist_ok=True)
    with open(TMP_DRIVE_AUTH, "w") as token:
        token.write(creds.to_json())


def _call_sixgpt_api_server() -> T.Optional[Credentials]:
    url_response = requests.get(f"{API_URL}/v1/drive/get-url")
    if url_response.status_code != 200:
        return
    url = url_response.json()["url"]
    click.echo(f"Copy and paste this URL into your browser: {url}")
    code = click.prompt("Paste your code")
    code_response = requests.get(f"{API_URL}/v1/drive/callback?code={code}")
    code_response.raise_for_status()
    if code_response.status_code != 200:
        return
    resp = code_response.json()["tokens"]
    return _form_credentials_from_token(resp)


def _call_sixgpt_api_server_refresh(creds: Credentials) -> T.Optional[Credentials]:
    url_response = requests.get(
        f"{API_URL}/v1/drive/refresh-token?refreshToken={creds.token}"
    )
    if url_response.status_code != 200:
        return
    resp = url_response.json()["tokens"]
    return _form_credentials_from_token(resp)


def _form_credentials_from_token(resp: T.Dict[str, T.Any]) -> Credentials:
    code = {
        "token": resp["access_token"],
        "scopes": [resp["scope"]],
        "expiry": dt.datetime.fromtimestamp(
            resp["expiry_date"] / 1000, dt.timezone.utc
        ),
    }
    return Credentials(**code)

async def write_uuid_file(data: bytes) -> str:
    """Uploads a file to the sixgpt drive bucket with a random UUID.

    Args:
        data: The data to upload.

    Returns:
        The URL of the uploaded file.
    """
    creds = get_active_account()
    if not creds:
        raise Exception("No active drive account found.")
    service = build("drive", "v3", credentials=creds)

    # Check if the folder already exists
    query = f"name='{BASE_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)")
        .execute()
    )
    items = results.get("files", [])
    if items:
        folder_id = items[0]["id"]
    else:
        # Create sixgpt folder if it did not exist
        folder_metadata = {
            "name": BASE_NAME,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = service.files().create(body=folder_metadata).execute()
        folder_id = folder.get("id")

    uuid_path = str(uuid4())
    file_metadata = {"name": uuid_path, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype="application/zip")
    resp = service.files().create(body=file_metadata, media_body=media).execute()

    # Make the file publicly shareable
    permission = {"type": "anyone", "role": "reader", "allowFileDiscovery": False}
    service.permissions().create(fileId=resp["id"], body=permission).execute()

    # Get the downloadable link
    file = service.files().get(fileId=resp["id"], fields="webContentLink").execute()
    downloadable_link = file.get("webContentLink")
    return downloadable_link
