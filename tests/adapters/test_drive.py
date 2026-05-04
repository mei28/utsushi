"""Unit tests for the Drive adapter.

Network-bound tests are excluded; the Google API client is mocked.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from utsushi.adapters import drive


def test_credentials_path_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UTSUSHI_CREDENTIALS", raising=False)
    assert drive.credentials_path() == Path.home() / ".config" / "utsushi" / "credentials.json"


def test_credentials_path_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    p = tmp_path / "creds.json"
    monkeypatch.setenv("UTSUSHI_CREDENTIALS", str(p))
    assert drive.credentials_path() == p


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://docs.google.com/presentation/d/1abcXYZ_-ID/edit", "1abcXYZ_-ID"),
        ("https://docs.google.com/presentation/d/1abcXYZ_-ID/edit#slide=id.p1", "1abcXYZ_-ID"),
        ("https://docs.google.com/presentation/d/1abcXYZ_-ID", "1abcXYZ_-ID"),
        ("1abcXYZ_-ID", "1abcXYZ_-ID"),  # raw file id passes through
    ],
)
def test_parse_file_id(url: str, expected: str) -> None:
    assert drive.parse_file_id(url) == expected


def test_parse_file_id_rejects_unrecognized() -> None:
    with pytest.raises(ValueError, match="not a Drive presentation URL"):
        drive.parse_file_id("https://example.com/foo")


def test_load_credentials_uses_cached_token_if_valid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A valid cached token should bypass the OAuth flow entirely."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text("{}")
    monkeypatch.setenv("UTSUSHI_CREDENTIALS", str(creds_file))

    class FakeCreds:
        valid = True
        expired = False

        def to_json(self) -> str:
            return "{}"

    monkeypatch.setattr(drive, "_read_token", lambda: FakeCreds())
    # If anyone reaches the OAuth flow, the test fails — flow takes a port.
    monkeypatch.setattr(drive, "_run_oauth_flow", lambda creds_file: pytest.fail("must not run"))

    result = drive.load_credentials()
    assert isinstance(result, FakeCreds)


def test_load_credentials_refreshes_expired_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text("{}")
    monkeypatch.setenv("UTSUSHI_CREDENTIALS", str(creds_file))

    refreshed: list[bool] = []

    class FakeCreds:
        valid = False
        expired = True
        refresh_token = "rt"

        def refresh(self, request: object) -> None:
            self.valid = True
            refreshed.append(True)

        def to_json(self) -> str:
            return "{}"

    monkeypatch.setattr(drive, "_read_token", lambda: FakeCreds())
    monkeypatch.setattr(drive, "_write_token", lambda creds: None)
    monkeypatch.setattr(drive, "_run_oauth_flow", lambda creds_file: pytest.fail("must not run"))

    drive.load_credentials()
    assert refreshed == [True]


def test_load_credentials_runs_flow_when_no_cached_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text("{}")
    monkeypatch.setenv("UTSUSHI_CREDENTIALS", str(creds_file))

    class FakeCreds:
        valid = True
        expired = False

        def to_json(self) -> str:
            return "{}"

    flow_calls: list[Path] = []

    def fake_flow(creds_path: Path) -> FakeCreds:
        flow_calls.append(creds_path)
        return FakeCreds()

    monkeypatch.setattr(drive, "_read_token", lambda: None)
    monkeypatch.setattr(drive, "_run_oauth_flow", fake_flow)
    monkeypatch.setattr(drive, "_write_token", lambda creds: None)

    drive.load_credentials()
    assert flow_calls == [creds_file]


def test_load_credentials_missing_credentials_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("UTSUSHI_CREDENTIALS", str(tmp_path / "missing.json"))
    monkeypatch.setattr(drive, "_read_token", lambda: None)
    with pytest.raises(FileNotFoundError, match="credentials.json"):
        drive.load_credentials()


class _FakeFiles:
    def __init__(self) -> None:
        self.create_kwargs: dict[str, object] | None = None
        self.export_kwargs: dict[str, object] | None = None
        self._next_create_response: dict[str, str] = {"id": "FILE_ID_X"}
        self._export_payload: bytes = b""

    def configure_export(self, payload: bytes) -> None:
        self._export_payload = payload

    def create(self, **kwargs: object) -> _FakeRequest:
        self.create_kwargs = kwargs
        return _FakeRequest(self._next_create_response)

    def export_media(self, **kwargs: object) -> _FakeMediaRequest:
        self.export_kwargs = kwargs
        return _FakeMediaRequest(self._export_payload)


class _FakeRequest:
    def __init__(self, response: dict[str, str]) -> None:
        self._response = response

    def execute(self) -> dict[str, str]:
        return self._response


class _FakeMediaRequest:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    @property
    def uri(self) -> str:
        return "fake://export"


class _FakeService:
    def __init__(self) -> None:
        self._files = _FakeFiles()

    def files(self) -> _FakeFiles:
        return self._files


def test_upload_as_slides_invokes_drive_create(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    src = tmp_path / "deck.pptx"
    src.write_bytes(b"PK\x03\x04")

    service = _FakeService()
    monkeypatch.setattr(drive, "_build_service", lambda: service)

    file_id = drive.upload_as_slides(src)
    assert file_id == "FILE_ID_X"

    create_kwargs = service.files().create_kwargs
    assert create_kwargs is not None
    body = create_kwargs["body"]
    assert isinstance(body, dict)
    assert body["mimeType"] == "application/vnd.google-apps.presentation"
    assert body["name"] == "deck"


def test_upload_as_slides_with_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    src = tmp_path / "deck.pptx"
    src.write_bytes(b"PK\x03\x04")
    service = _FakeService()
    monkeypatch.setattr(drive, "_build_service", lambda: service)

    drive.upload_as_slides(src, folder_id="FOLDER_ABC")
    body = service.files().create_kwargs["body"]  # type: ignore[index]
    assert isinstance(body, dict)
    assert body["parents"] == ["FOLDER_ABC"]


def test_upload_as_slides_rejects_non_pptx(tmp_path: Path) -> None:
    src = tmp_path / "deck.key"
    src.write_text("fake")
    with pytest.raises(ValueError, match="\\.pptx"):
        drive.upload_as_slides(src)


def test_export_as_pptx_writes_blob(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = b"PK\x03\x04fake-pptx"
    service = _FakeService()
    service.files().configure_export(payload)
    monkeypatch.setattr(drive, "_build_service", lambda: service)
    monkeypatch.setattr(drive, "_download", lambda request: payload)

    dst = tmp_path / "out.pptx"
    drive.export_as_pptx("FILE_ID_X", dst)
    assert dst.read_bytes() == payload

    export_kwargs = service.files().export_kwargs
    assert export_kwargs is not None
    assert export_kwargs["fileId"] == "FILE_ID_X"
    assert (
        export_kwargs["mimeType"]
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
