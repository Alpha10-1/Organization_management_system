"""File storage abstraction.

Two backends are supported, selected via the STORAGE_BACKEND env var:

- ``local`` (default): files live on local disk under UPLOAD_DIR. This is
  the original behaviour and remains the zero-config path for local dev.
- ``s3``: files live in an S3-compatible bucket (AWS S3, MinIO, Cloudflare
  R2, etc). Configure with S3_BUCKET plus, for non-AWS endpoints,
  S3_ENDPOINT_URL. Credentials are picked up the normal boto3 way (env
  vars, shared config file, or an instance/task role) -- nothing
  S3-specific needs to be hardcoded here.

Callers (app.routes.files) only interact with the small StorageBackend
interface below and a backend-agnostic ``key`` (the file's stored_name),
so switching backends is a config change, not a code change.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import BinaryIO, Optional

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class StorageBackend:
    """Common interface every storage backend implements."""

    def save(self, key: str, fileobj: BinaryIO) -> None:
        """Persist the contents of fileobj (seekable, at any position)
        under `key`."""
        raise NotImplementedError

    def delete(self, key: str) -> None:
        """Remove the object. Must not raise if it's already gone -- soft
        delete in the DB is the source of truth, this is best-effort
        cleanup and callers shouldn't have to special-case a missing file."""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def local_path(self, key: str) -> Optional[str]:
        """Return an on-disk path for `key` if the backend has one
        (local only). Backends without a native filesystem path (S3)
        return None -- callers should use read_bytes/download_to instead."""
        return None

    def read_bytes(self, key: str) -> bytes:
        """Return the full object contents. Fine for our use case since
        uploads are already capped (MAX_UPLOAD_SIZE_MB, 25MB by default)."""
        raise NotImplementedError

    def download_to(self, key: str, dest_path: str) -> None:
        """Write the object to a local path, e.g. for zipping multiple
        files together."""
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """Original behaviour: files on local disk under UPLOAD_DIR."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.getenv("UPLOAD_DIR", str(_BACKEND_ROOT / "uploads")))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.base_dir / key

    def save(self, key: str, fileobj: BinaryIO) -> None:
        fileobj.seek(0)
        with self._path(key).open("wb") as out:
            shutil.copyfileobj(fileobj, out)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def local_path(self, key: str) -> Optional[str]:
        return str(self._path(key))

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def download_to(self, key: str, dest_path: str) -> None:
        shutil.copyfile(self._path(key), dest_path)


class S3StorageBackend(StorageBackend):
    """S3-compatible backend. Works against real AWS S3 as well as any
    S3-compatible endpoint (MinIO, R2, etc) via S3_ENDPOINT_URL, which
    makes it usable for local/self-hosted dev too -- not just prod AWS."""

    def __init__(
        self,
        bucket: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region: Optional[str] = None,
        prefix: Optional[str] = None,
    ):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - exercised only when misconfigured
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requires the boto3 package. Install it with "
                "`pip install boto3` (it's already listed in requirements.txt)."
            ) from exc

        self.bucket = bucket or os.getenv("S3_BUCKET")
        if not self.bucket:
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requires S3_BUCKET to be set to the target bucket name."
            )
        self.prefix = (prefix if prefix is not None else os.getenv("S3_PREFIX", "")).strip("/")

        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or os.getenv("S3_ENDPOINT_URL") or None,
            region_name=region or os.getenv("S3_REGION") or None,
        )

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def save(self, key: str, fileobj: BinaryIO) -> None:
        fileobj.seek(0)
        self._client.upload_fileobj(fileobj, self.bucket, self._key(key))

    def delete(self, key: str) -> None:
        # delete_object is idempotent on S3 -- a missing key is not an error.
        self._client.delete_object(Bucket=self.bucket, Key=self._key(key))

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except ClientError:
            return False

    def local_path(self, key: str) -> Optional[str]:
        return None

    def read_bytes(self, key: str) -> bytes:
        import io

        buffer = io.BytesIO()
        self._client.download_fileobj(self.bucket, self._key(key), buffer)
        return buffer.getvalue()

    def download_to(self, key: str, dest_path: str) -> None:
        self._client.download_file(self.bucket, self._key(key), dest_path)

    def presigned_url(self, key: str, expires_in: int = 300) -> str:
        """Optional convenience for callers that would rather redirect the
        client straight to S3 than proxy bytes through our API."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": self._key(key)},
            ExpiresIn=expires_in,
        )


_backend_instance: Optional[StorageBackend] = None


def get_storage_backend() -> StorageBackend:
    """Return the process-wide storage backend, built from env vars on
    first use. Cached like a singleton -- same pattern as the old
    module-level UPLOAD_DIR constant it replaces."""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = _build_backend()
    return _backend_instance


def _build_backend() -> StorageBackend:
    backend_name = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if backend_name == "s3":
        return S3StorageBackend()
    if backend_name not in ("local", ""):
        raise RuntimeError(
            f"Unknown STORAGE_BACKEND '{backend_name}'. Use 'local' or 's3'."
        )
    return LocalStorageBackend()


def reset_storage_backend_cache() -> None:
    """Test hook: force the next get_storage_backend() call to rebuild,
    so tests can flip STORAGE_BACKEND/UPLOAD_DIR between cases."""
    global _backend_instance
    _backend_instance = None
