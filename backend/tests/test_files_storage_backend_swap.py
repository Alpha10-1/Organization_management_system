"""Route-level proof that app.routes.files only talks to the storage
abstraction (app.core.storage.StorageBackend), not local disk directly.

We swap the module-level `storage` singleton for an in-memory fake that
deliberately has no local_path() (like S3StorageBackend), then drive the
upload/download/bulk-download endpoints through it. If any route still
reached for a raw filesystem path, this would fail even though the local
disk backend tests all pass -- that's the gap this test closes."""

import io
import zipfile

import pytest

import app.routes.files as files_route
from app.core.storage import StorageBackend


class InMemoryStorageBackend(StorageBackend):
    """Minimal fake with the same shape as S3StorageBackend: no
    local_path(), everything keyed in a plain dict."""

    def __init__(self):
        self._objects: dict[str, bytes] = {}

    def save(self, key, fileobj):
        fileobj.seek(0)
        self._objects[key] = fileobj.read()

    def delete(self, key):
        self._objects.pop(key, None)

    def exists(self, key):
        return key in self._objects

    def local_path(self, key):
        return None

    def read_bytes(self, key):
        return self._objects[key]

    def download_to(self, key, dest_path):
        with open(dest_path, "wb") as f:
            f.write(self._objects[key])


@pytest.fixture
def fake_storage(monkeypatch):
    fake = InMemoryStorageBackend()
    monkeypatch.setattr(files_route, "storage", fake)
    return fake


def test_upload_and_download_roundtrip_without_local_path(admin_client, fake_storage):
    resp = admin_client.post(
        "/files/upload",
        files={"file": ("report.txt", io.BytesIO(b"quarterly numbers"), "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    record = resp.json()

    # Nothing hit local disk -- the object only exists in our fake store.
    assert len(fake_storage._objects) == 1

    download = admin_client.get(f"/files/{record['id']}/download")
    assert download.status_code == 200
    assert download.content == b"quarterly numbers"
    assert "report.txt" in download.headers.get("content-disposition", "")


def test_download_404s_when_object_missing_from_backend(admin_client, fake_storage):
    resp = admin_client.post(
        "/files/upload",
        files={"file": ("gone.txt", io.BytesIO(b"x"), "text/plain")},
    )
    record = resp.json()

    # Simulate the object having disappeared from the backend (e.g. bucket
    # lifecycle rule) without the DB row knowing.
    fake_storage._objects.clear()

    download = admin_client.get(f"/files/{record['id']}/download")
    assert download.status_code == 404


def test_bulk_download_zips_objects_from_backend(admin_client, fake_storage):
    ids = []
    for name, content in [("a.txt", b"aaa"), ("b.txt", b"bbb")]:
        resp = admin_client.post(
            "/files/upload",
            files={"file": (name, io.BytesIO(content), "text/plain")},
        )
        ids.append(resp.json()["id"])

    resp = admin_client.post("/files/bulk/download", json={"file_ids": ids})
    assert resp.status_code == 200

    archive = zipfile.ZipFile(io.BytesIO(resp.content))
    names = set(archive.namelist())
    assert names == {"a.txt", "b.txt"}
    assert archive.read("a.txt") == b"aaa"
    assert archive.read("b.txt") == b"bbb"


def test_upload_rejected_over_size_limit_never_reaches_backend(admin_client, fake_storage, monkeypatch):
    monkeypatch.setattr(files_route, "MAX_UPLOAD_SIZE_BYTES", 10)

    resp = admin_client.post(
        "/files/upload",
        files={"file": ("big.txt", io.BytesIO(b"x" * 100), "text/plain")},
    )

    assert resp.status_code == 413
    # The whole point of validating before storage.save(): a rejected
    # upload should never have touched the backend at all.
    assert len(fake_storage._objects) == 0
