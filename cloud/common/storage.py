"""Unified storage abstraction supporting local filesystem and Amazon S3."""

import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from cloud.common.config import CloudConfig, get_config


def _normalize_key(key: str) -> str:
    clean = key.replace("\\", "/").lstrip("/")
    if not clean:
        raise ValueError("Storage key cannot be empty")
    parts = [p for p in clean.split("/") if p]
    if any(p == ".." for p in parts):
        raise ValueError(f"Invalid storage key containing parent traversal: {key!r}")
    return "/".join(parts)


class StorageBackend(ABC):
    """Abstract key-object storage interface shared by local and AWS runners."""

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def read_bytes(self, key: str) -> bytes: ...

    @abstractmethod
    def write_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str: ...

    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]: ...

    @abstractmethod
    def uri_for(self, key: str) -> str: ...

    def presign_url(self, key: str, expires_in: int = 900) -> str:
        """Return a readable URI or presigned HTTP URL for the object."""
        return self.uri_for(key)

    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        return self.read_bytes(key).decode(encoding)

    def write_text(self, key: str, text: str, encoding: str = "utf-8", content_type: Optional[str] = "text/plain") -> str:
        return self.write_bytes(key, text.encode(encoding), content_type=content_type)

    def read_json(self, key: str) -> Any:
        return json.loads(self.read_text(key))

    def write_json(self, key: str, obj: Any, indent: int = 2) -> str:
        payload = json.dumps(obj, indent=indent, ensure_ascii=False, default=str)
        return self.write_text(key, payload, content_type="application/json")

    def read_jsonl(self, key: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for line in self.read_text(key).splitlines():
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
        return rows

    def write_jsonl(self, key: str, rows: Iterable[Dict[str, Any]]) -> str:
        lines = [json.dumps(row, ensure_ascii=False, default=str) for row in rows]
        payload = ("\n".join(lines) + "\n") if lines else ""
        return self.write_text(key, payload, content_type="application/x-ndjson")


class LocalStorage(StorageBackend):
    """Local filesystem storage mirroring S3 prefixes with atomic writes."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        clean = _normalize_key(key)
        target = (self.root / clean).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"Key escapes storage root: {key!r}")
        return target

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def read_bytes(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise FileNotFoundError(f"Object not found in local storage: {key}")
        return path.read_bytes()

    def write_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp_name, path)
        except Exception:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise
        return self.uri_for(key)

    def list_keys(self, prefix: str = "") -> List[str]:
        clean_prefix = prefix.replace("\\", "/").lstrip("/")
        keys: List[str] = []
        for path in self.root.rglob("*"):
            if not path.is_file() or path.name.startswith(".tmp_"):
                continue
            rel = path.relative_to(self.root).as_posix()
            if rel.startswith(clean_prefix):
                keys.append(rel)
        return sorted(keys)

    def uri_for(self, key: str) -> str:
        return self._resolve(key).as_uri()


class S3Storage(StorageBackend):
    """Amazon S3 storage backend with adaptive retries and lazy boto3 import."""

    def __init__(self, bucket: str, region: str = "ap-south-1", client: Any = None) -> None:
        self.bucket = bucket
        self.region = region
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        import boto3
        from botocore.config import Config

        cfg = Config(region_name=self.region, retries={"max_attempts": 5, "mode": "adaptive"})
        self._client = boto3.client("s3", config=cfg)
        return self._client

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        clean = _normalize_key(key)
        try:
            self._get_client().head_object(Bucket=self.bucket, Key=clean)
            return True
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in ("404", "NoSuchKey", "NotFound") or status == 404:
                return False
            raise

    def read_bytes(self, key: str) -> bytes:
        clean = _normalize_key(key)
        resp = self._get_client().get_object(Bucket=self.bucket, Key=clean)
        return resp["Body"].read()

    def write_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        clean = _normalize_key(key)
        kwargs: Dict[str, Any] = {"Bucket": self.bucket, "Key": clean, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        self._get_client().put_object(**kwargs)
        return self.uri_for(clean)

    def list_keys(self, prefix: str = "") -> List[str]:
        clean_prefix = prefix.replace("\\", "/").lstrip("/")
        paginator = self._get_client().get_paginator("list_objects_v2")
        keys: List[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=clean_prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return sorted(keys)

    def uri_for(self, key: str) -> str:
        clean = _normalize_key(key)
        return f"s3://{self.bucket}/{clean}"

    def presign_url(self, key: str, expires_in: int = 900) -> str:
        clean = _normalize_key(key)
        return self._get_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": clean},
            ExpiresIn=expires_in,
        )


def get_storage(config: Optional[CloudConfig] = None) -> StorageBackend:
    """Instantiate the configured storage backend."""
    cfg = config or get_config()
    if cfg.storage_backend == "s3":
        return S3Storage(bucket=cfg.s3_bucket, region=cfg.aws_region)
    return LocalStorage(root=cfg.local_datalake_dir)
