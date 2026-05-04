"""Google Drive adapter — OAuth flow + Slides upload/export.

Each user provides their own ``credentials.json`` (OAuth desktop client
from their own GCP project). The path defaults to
``~/.config/utsushi/credentials.json`` and can be overridden via the
``UTSUSHI_CREDENTIALS`` environment variable.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

if TYPE_CHECKING:
    pass

# Drive mime types for the conversions we drive.
_MIME_SLIDES = "application/vnd.google-apps.presentation"
_MIME_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

# OAuth scope. drive.file restricts utsushi to files it created or that
# the user explicitly opened with utsushi, which is the right least-
# privilege boundary for a CLI converter.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# keyring slot for the cached OAuth token JSON.
_KEYRING_SERVICE = "utsushi"
_KEYRING_USERNAME = "drive-oauth-token"

_DRIVE_PRESENTATION_URL = re.compile(
    r"https?://docs\.google\.com/presentation/d/(?P<id>[A-Za-z0-9_-]+)"
)
_FILE_ID_ONLY = re.compile(r"^[A-Za-z0-9_-]+$")


def credentials_path() -> Path:
    """Resolve the credentials.json path, honoring UTSUSHI_CREDENTIALS."""
    override = os.environ.get("UTSUSHI_CREDENTIALS")
    if override:
        return Path(override)
    return Path.home() / ".config" / "utsushi" / "credentials.json"


def parse_file_id(url_or_id: str) -> str:
    """Extract a Drive file id from a presentation URL or accept a raw id."""
    match = _DRIVE_PRESENTATION_URL.search(url_or_id)
    if match:
        return match.group("id")
    if _FILE_ID_ONLY.match(url_or_id):
        return url_or_id
    raise ValueError(f"not a Drive presentation URL or file id: {url_or_id!r}")


def _read_token() -> Credentials | None:
    """Load the cached OAuth token from the macOS Keychain (or platform default)."""
    raw = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
    if not raw:
        return None
    return Credentials.from_authorized_user_info(_loads(raw), SCOPES)


def _write_token(creds: Credentials) -> None:
    keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, creds.to_json())


def _run_oauth_flow(creds_file: Path) -> Credentials:
    """Run the OAuth desktop flow against the user's credentials.json."""
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    return flow.run_local_server(port=0)


def _loads(raw: str) -> dict[str, Any]:
    """Parse a token JSON string. Indirected so the import stays at module top."""
    import json

    parsed: dict[str, Any] = json.loads(raw)
    return parsed


def _build_service() -> Any:
    """Construct the authenticated Drive v3 service. Indirected for test patching."""
    return build("drive", "v3", credentials=load_credentials(), cache_discovery=False)


def _download(request: Any) -> bytes:
    """Stream a Drive media request into memory."""
    import io

    from googleapiclient.http import MediaIoBaseDownload

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def upload_as_slides(src: Path, folder_id: str | None = None) -> str:
    """Upload a .pptx to Drive, converting it to a Google Slides presentation."""
    if src.suffix.lower() != ".pptx":
        raise ValueError(f"upload_as_slides requires a .pptx, got {src.suffix!r}")
    if not src.exists():
        raise FileNotFoundError(src)

    body: dict[str, Any] = {"name": src.stem, "mimeType": _MIME_SLIDES}
    if folder_id:
        body["parents"] = [folder_id]

    media = MediaFileUpload(str(src), mimetype=_MIME_PPTX, resumable=True)
    service = _build_service()
    response = service.files().create(body=body, media_body=media, fields="id").execute()
    return str(response["id"])


def export_as_pptx(file_id: str, dst: Path) -> None:
    """Download a Google Slides presentation as .pptx."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    service = _build_service()
    request = service.files().export_media(fileId=file_id, mimeType=_MIME_PPTX)
    blob = _download(request)
    dst.write_bytes(blob)


def load_credentials() -> Credentials:
    """Return valid Drive credentials, prompting the OAuth flow if necessary."""
    creds = _read_token()

    if creds is not None and creds.valid:
        return creds

    if creds is not None and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _write_token(creds)
        return creds

    creds_file = credentials_path()
    if not creds_file.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {creds_file}. "
            "Create an OAuth desktop client in your GCP project, download the "
            "JSON, and place it there (or set UTSUSHI_CREDENTIALS)."
        )
    creds = _run_oauth_flow(creds_file)
    _write_token(creds)
    return creds
