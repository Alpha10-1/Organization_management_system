"""Tests for app.core.storage -- the pluggable local/S3 file storage
backend. These are pure unit tests against the StorageBackend interface
(no HTTP layer), so they don't depend on the admin_client/staff_client
fixtures. S3 is exercised against a stubbed boto3 client rather than a
real bucket, matching this repo's existing preference for fast, offline
tests over hitting real infrastructure."""

import io
from unittest.mock import MagicMock, patch

import pytest

from app.core.storage import (
    LocalStorageBackend,
    S3StorageBackend,
    _build_backend,
    get_storage_backend,
    reset_storage_backend_cache,
)


# --------------------------------------------------------------------------
# Local backend
# --------------------------------------------------------------------------


def test_local_backend_save_and_read_roundtrip(tmp_path):
    backend = LocalStorageBackend(base_dir=str(tmp_path))
    backend.save("abc123.txt", io.BytesIO(b"hello world"))

    assert backend.exists("abc123.txt") is True
    assert backend.read_bytes("abc123.txt") == b"hello world"


def test_local_backend_local_path_points_at_base_dir(tmp_path):
    backend = LocalStorageBackend(base_dir=str(tmp_path))
    backend.save("abc123.txt", io.BytesIO(b"data"))

    path = backend.local_path("abc123.txt")
    assert path == str(tmp_path / "abc123.txt")
    assert (tmp_path / "abc123.txt").read_bytes() == b"data"


def test_local_backend_exists_false_for_missing_key(tmp_path):
    backend = LocalStorageBackend(base_dir=str(tmp_path))
    assert backend.exists("nope.txt") is False


def test_local_backend_delete_is_idempotent(tmp_path):
    backend = LocalStorageBackend(base_dir=str(tmp_path))
    backend.save("abc.txt", io.BytesIO(b"x"))

    backend.delete("abc.txt")
    assert backend.exists("abc.txt") is False

    # Deleting again (already gone) must not raise.
    backend.delete("abc.txt")


def test_local_backend_download_to_copies_file(tmp_path):
    backend = LocalStorageBackend(base_dir=str(tmp_path))
    backend.save("abc.txt", io.BytesIO(b"payload"))

    dest = tmp_path / "elsewhere" / "copy.txt"
    dest.parent.mkdir()
    backend.download_to("abc.txt", str(dest))

    assert dest.read_bytes() == b"payload"


def test_local_backend_creates_base_dir_if_missing(tmp_path):
    target = tmp_path / "does" / "not" / "exist"
    assert not target.exists()

    LocalStorageBackend(base_dir=str(target))
    assert target.exists()


# --------------------------------------------------------------------------
# S3 backend (mocked boto3 client -- no network/real bucket involved)
# --------------------------------------------------------------------------


def _make_s3_backend(**kwargs):
    fake_client = MagicMock()
    with patch("boto3.client", return_value=fake_client) as mock_ctor:
        backend = S3StorageBackend(bucket="test-bucket", **kwargs)
    return backend, fake_client, mock_ctor


def test_s3_backend_requires_bucket():
    with patch("boto3.client", return_value=MagicMock()):
        with pytest.raises(RuntimeError, match="S3_BUCKET"):
            S3StorageBackend(bucket=None)


def test_s3_backend_save_calls_upload_fileobj():
    backend, client, _ = _make_s3_backend()
    fileobj = io.BytesIO(b"content")

    backend.save("key1.txt", fileobj)

    client.upload_fileobj.assert_called_once()
    args, _ = client.upload_fileobj.call_args
    assert args[0] is fileobj
    assert args[1] == "test-bucket"
    assert args[2] == "key1.txt"


def test_s3_backend_applies_prefix_to_keys():
    backend, client, _ = _make_s3_backend(prefix="uploads")

    backend.save("key1.txt", io.BytesIO(b"x"))
    backend.delete("key1.txt")

    _, _, upload_key = client.upload_fileobj.call_args[0]
    assert upload_key == "uploads/key1.txt"
    assert client.delete_object.call_args.kwargs["Key"] == "uploads/key1.txt"


def test_s3_backend_delete_calls_delete_object():
    backend, client, _ = _make_s3_backend()

    backend.delete("key1.txt")

    client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="key1.txt")


def test_s3_backend_exists_true_when_head_object_succeeds():
    backend, client, _ = _make_s3_backend()
    client.head_object.return_value = {}

    assert backend.exists("key1.txt") is True


def test_s3_backend_exists_false_on_client_error():
    from botocore.exceptions import ClientError

    backend, client, _ = _make_s3_backend()
    client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
    )

    assert backend.exists("missing.txt") is False


def test_s3_backend_local_path_is_none():
    backend, _, _ = _make_s3_backend()
    assert backend.local_path("key1.txt") is None


def test_s3_backend_read_bytes_downloads_into_buffer():
    backend, client, _ = _make_s3_backend()

    def fake_download_fileobj(bucket, key, buffer):
        buffer.write(b"remote-content")

    client.download_fileobj.side_effect = fake_download_fileobj

    assert backend.read_bytes("key1.txt") == b"remote-content"


def test_s3_backend_download_to_calls_download_file():
    backend, client, _ = _make_s3_backend()

    backend.download_to("key1.txt", "/tmp/somewhere.txt")

    client.download_file.assert_called_once_with("test-bucket", "key1.txt", "/tmp/somewhere.txt")


def test_s3_backend_presigned_url_delegates_to_client():
    backend, client, _ = _make_s3_backend()
    client.generate_presigned_url.return_value = "https://example.com/signed"

    url = backend.presigned_url("key1.txt", expires_in=60)

    assert url == "https://example.com/signed"
    client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "test-bucket", "Key": "key1.txt"},
        ExpiresIn=60,
    )


# --------------------------------------------------------------------------
# Backend selection (get_storage_backend / _build_backend)
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache_around_test():
    reset_storage_backend_cache()
    yield
    reset_storage_backend_cache()


def test_build_backend_defaults_to_local(monkeypatch, tmp_path):
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

    backend = _build_backend()

    assert isinstance(backend, LocalStorageBackend)


def test_build_backend_explicit_local(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

    backend = _build_backend()

    assert isinstance(backend, LocalStorageBackend)


def test_build_backend_s3_selected_via_env(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "env-bucket")

    with patch("boto3.client", return_value=MagicMock()):
        backend = _build_backend()

    assert isinstance(backend, S3StorageBackend)
    assert backend.bucket == "env-bucket"


def test_build_backend_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "dropbox")

    with pytest.raises(RuntimeError, match="Unknown STORAGE_BACKEND"):
        _build_backend()


def test_get_storage_backend_is_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

    first = get_storage_backend()
    second = get_storage_backend()

    assert first is second
