"""
Storage Integration Client

Supports multiple storage backends:
- local: Local filesystem (for development without S3)
- minio: MinIO S3-compatible storage
- b2: Backblaze B2 cloud storage
"""

import io
import json
import os
import shutil
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, BinaryIO, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import mimetypes

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class StorageObject:
    key: str
    size: int
    last_modified: datetime
    etag: str
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class BaseStorageClient(ABC):
    """Abstract base class for storage clients."""
    
    @abstractmethod
    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> str:
        pass
    
    @abstractmethod
    def download_bytes(self, key: str) -> bytes:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def list_objects(self, prefix: str = "", recursive: bool = True, max_keys: Optional[int] = None) -> List[StorageObject]:
        pass
    
    @abstractmethod
    def get_presigned_url(self, key: str, expires: timedelta = timedelta(hours=1), method: str = "GET") -> str:
        pass
    
    def _get_content_type(self, key: str) -> str:
        content_type, _ = mimetypes.guess_type(key)
        return content_type or "application/octet-stream"
    
    def upload_json(self, key: str, data: Any, metadata: Optional[Dict[str, str]] = None) -> str:
        json_bytes = json.dumps(data, indent=2, default=str).encode("utf-8")
        return self.upload_bytes(key, json_bytes, content_type="application/json", metadata=metadata)
    
    def upload_markdown(self, key: str, content: str, metadata: Optional[Dict[str, str]] = None) -> str:
        md_bytes = content.encode("utf-8")
        return self.upload_bytes(key, md_bytes, content_type="text/markdown", metadata=metadata)
    
    def download_json(self, key: str) -> Any:
        data = self.download_bytes(key)
        return json.loads(data.decode("utf-8"))


class LocalStorageClient(BaseStorageClient):
    """Local filesystem storage for development."""
    
    def __init__(self, base_path: str = None, base_url: str = None):
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.base_url = base_url or settings.LOCAL_STORAGE_BASE_URL
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorageClient initialized at {self.base_path}")
    
    def _get_full_path(self, key: str) -> Path:
        return self.base_path / key
    
    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> str:
        file_path = self._get_full_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_bytes(data)
        
        if metadata:
            meta_path = file_path.with_suffix(file_path.suffix + ".meta")
            meta_path.write_text(json.dumps(metadata))
        
        logger.info(f"Uploaded {len(data)} bytes to {key}")
        return key
    
    def upload_file(self, key: str, file_path: Union[str, Path], content_type: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> str:
        source_path = Path(file_path)
        dest_path = self._get_full_path(key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source_path, dest_path)
        
        if metadata:
            meta_path = dest_path.with_suffix(dest_path.suffix + ".meta")
            meta_path.write_text(json.dumps(metadata))
        
        logger.info(f"Uploaded file {file_path} to {key}")
        return key
    
    def download_bytes(self, key: str) -> bytes:
        file_path = self._get_full_path(key)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return file_path.read_bytes()
    
    def download_file(self, key: str, file_path: Union[str, Path]) -> Path:
        dest_path = Path(file_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        source_path = self._get_full_path(key)
        shutil.copy2(source_path, dest_path)
        
        return dest_path
    
    def delete(self, key: str) -> bool:
        file_path = self._get_full_path(key)
        try:
            file_path.unlink(missing_ok=True)
            meta_path = file_path.with_suffix(file_path.suffix + ".meta")
            meta_path.unlink(missing_ok=True)
            return True
        except Exception:
            return False
    
    def delete_many(self, keys: List[str]) -> int:
        deleted = 0
        for key in keys:
            if self.delete(key):
                deleted += 1
        return deleted
    
    def delete_prefix(self, prefix: str) -> int:
        objects = self.list_objects(prefix=prefix)
        return self.delete_many([obj.key for obj in objects])
    
    def exists(self, key: str) -> bool:
        return self._get_full_path(key).exists()
    
    def get_info(self, key: str) -> Optional[StorageObject]:
        file_path = self._get_full_path(key)
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        content = file_path.read_bytes()
        etag = hashlib.md5(content).hexdigest()
        
        return StorageObject(
            key=key,
            size=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            etag=etag,
            content_type=self._get_content_type(key),
        )
    
    def list_objects(self, prefix: str = "", recursive: bool = True, max_keys: Optional[int] = None) -> List[StorageObject]:
        objects = []
        search_path = self.base_path / prefix if prefix else self.base_path
        
        if not search_path.exists():
            return objects
        
        pattern = "**/*" if recursive else "*"
        
        for file_path in search_path.glob(pattern):
            if file_path.is_file() and not file_path.suffix == ".meta":
                key = str(file_path.relative_to(self.base_path))
                stat = file_path.stat()
                
                objects.append(StorageObject(
                    key=key,
                    size=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                    etag=hashlib.md5(file_path.read_bytes()).hexdigest(),
                    content_type=self._get_content_type(key),
                ))
                
                if max_keys and len(objects) >= max_keys:
                    break
        
        return objects
    
    def copy(self, source_key: str, dest_key: str, source_bucket: Optional[str] = None) -> str:
        source_path = self._get_full_path(source_key)
        dest_path = self._get_full_path(dest_key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source_path, dest_path)
        return dest_key
    
    def move(self, source_key: str, dest_key: str) -> str:
        self.copy(source_key, dest_key)
        self.delete(source_key)
        return dest_key
    
    def get_presigned_url(self, key: str, expires: timedelta = timedelta(hours=1), method: str = "GET") -> str:
        return f"{self.base_url}/{key}"
    
    def get_public_url(self, key: str) -> str:
        return f"{self.base_url}/{key}"


class S3StorageClient(BaseStorageClient):
    """S3-compatible storage client using MinIO."""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = False, provider: str = "minio"):
        from minio import Minio
        
        self.endpoint = endpoint
        self.bucket = bucket
        self.secure = secure
        self.provider = provider
        
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._ensure_bucket()
        logger.info(f"S3StorageClient initialized for {provider} at {endpoint}/{bucket}")
    
    def _ensure_bucket(self):
        from minio.error import S3Error
        try:
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as e:
            if e.code != "BucketAlreadyOwnedByYou":
                logger.error(f"Failed to ensure bucket: {e}")
                raise
    
    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> str:
        if content_type is None:
            content_type = self._get_content_type(key)
        
        stream = io.BytesIO(data)
        self._client.put_object(
            self.bucket, key, stream, length=len(data),
            content_type=content_type, metadata=metadata,
        )
        
        logger.info(f"Uploaded {len(data)} bytes to s3://{self.bucket}/{key}")
        return key
    
    def upload_file(self, key: str, file_path: Union[str, Path], content_type: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> str:
        file_path = Path(file_path)
        if content_type is None:
            content_type = self._get_content_type(str(file_path))
        
        self._client.fput_object(
            self.bucket, key, str(file_path),
            content_type=content_type, metadata=metadata,
        )
        
        logger.info(f"Uploaded file {file_path} to s3://{self.bucket}/{key}")
        return key
    
    def download_bytes(self, key: str) -> bytes:
        response = self._client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    
    def download_file(self, key: str, file_path: Union[str, Path]) -> Path:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.fget_object(self.bucket, key, str(file_path))
        return file_path
    
    def delete(self, key: str) -> bool:
        from minio.error import S3Error
        try:
            self._client.remove_object(self.bucket, key)
            return True
        except S3Error:
            return False
    
    def delete_many(self, keys: List[str]) -> int:
        from minio.deleteobjects import DeleteObject
        delete_objects = [DeleteObject(key) for key in keys]
        errors = list(self._client.remove_objects(self.bucket, delete_objects))
        return len(keys) - len(errors)
    
    def delete_prefix(self, prefix: str) -> int:
        objects = self.list_objects(prefix=prefix)
        return self.delete_many([obj.key for obj in objects])
    
    def exists(self, key: str) -> bool:
        from minio.error import S3Error
        try:
            self._client.stat_object(self.bucket, key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise
    
    def get_info(self, key: str) -> Optional[StorageObject]:
        from minio.error import S3Error
        try:
            stat = self._client.stat_object(self.bucket, key)
            return StorageObject(
                key=key,
                size=stat.size,
                last_modified=stat.last_modified,
                etag=stat.etag,
                content_type=stat.content_type,
                metadata=stat.metadata,
            )
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise
    
    def list_objects(self, prefix: str = "", recursive: bool = True, max_keys: Optional[int] = None) -> List[StorageObject]:
        objects = []
        for obj in self._client.list_objects(self.bucket, prefix=prefix, recursive=recursive):
            objects.append(StorageObject(
                key=obj.object_name,
                size=obj.size,
                last_modified=obj.last_modified,
                etag=obj.etag,
                content_type=obj.content_type,
            ))
            if max_keys and len(objects) >= max_keys:
                break
        return objects
    
    def copy(self, source_key: str, dest_key: str, source_bucket: Optional[str] = None) -> str:
        from minio.commonconfig import CopySource
        source_bucket = source_bucket or self.bucket
        self._client.copy_object(self.bucket, dest_key, CopySource(source_bucket, source_key))
        return dest_key
    
    def move(self, source_key: str, dest_key: str) -> str:
        self.copy(source_key, dest_key)
        self.delete(source_key)
        return dest_key
    
    def get_presigned_url(self, key: str, expires: timedelta = timedelta(hours=1), method: str = "GET") -> str:
        if method == "GET":
            return self._client.presigned_get_object(self.bucket, key, expires=expires)
        elif method == "PUT":
            return self._client.presigned_put_object(self.bucket, key, expires=expires)
        else:
            raise ValueError(f"Unsupported method: {method}")
    
    def get_public_url(self, key: str) -> str:
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{self.endpoint}/{self.bucket}/{key}"


class SEOmanStoragePaths:
    """Helper class for consistent storage paths."""
    
    @staticmethod
    def crawl_data(tenant_id: str, site_id: str, crawl_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/crawls/{crawl_id}/data.json"
    
    @staticmethod
    def crawl_pages(tenant_id: str, site_id: str, crawl_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/crawls/{crawl_id}/pages/"
    
    @staticmethod
    def audit_report(tenant_id: str, site_id: str, audit_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/audits/{audit_id}/report.json"
    
    @staticmethod
    def audit_issues(tenant_id: str, site_id: str, audit_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/audits/{audit_id}/issues.json"
    
    @staticmethod
    def keyword_data(tenant_id: str, site_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/keywords/"
    
    @staticmethod
    def content_brief(tenant_id: str, site_id: str, brief_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/content/briefs/{brief_id}.json"
    
    @staticmethod
    def content_draft(tenant_id: str, site_id: str, brief_id: str, draft_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/content/briefs/{brief_id}/drafts/{draft_id}.md"
    
    @staticmethod
    def export(tenant_id: str, export_type: str, export_id: str, filename: str) -> str:
        return f"tenants/{tenant_id}/exports/{export_type}/{export_id}/{filename}"
    
    @staticmethod
    def tenant_prefix(tenant_id: str) -> str:
        return f"tenants/{tenant_id}/"
    
    @staticmethod
    def site_prefix(tenant_id: str, site_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/"
    
    @staticmethod
    def report_base(tenant_id: str, site_id: str, report_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/"
    
    @staticmethod
    def audit_report_md(tenant_id: str, site_id: str, report_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/audit-report.md"
    
    @staticmethod
    def seo_plan_md(tenant_id: str, site_id: str, report_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/seo-plan.md"
    
    @staticmethod
    def page_fixes_md(tenant_id: str, site_id: str, report_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/page-fixes.md"
    
    @staticmethod
    def article_brief_md(tenant_id: str, site_id: str, report_id: str, brief_num: int, keyword_slug: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/briefs/article-{brief_num:02d}-{keyword_slug}.md"
    
    @staticmethod
    def report_metadata(tenant_id: str, site_id: str, report_id: str) -> str:
        return f"tenants/{tenant_id}/sites/{site_id}/reports/{report_id}/metadata.json"


_default_client: Optional[BaseStorageClient] = None


def get_storage_client() -> BaseStorageClient:
    """Get or create the default storage client based on settings."""
    global _default_client
    
    if _default_client is None:
        provider = getattr(settings, 'STORAGE_PROVIDER', 'local')
        logger.info(f"Initializing storage client with provider: {provider}")
        
        if provider == "local":
            _default_client = LocalStorageClient()
        elif provider == "b2":
            _default_client = S3StorageClient(
                endpoint=settings.B2_ENDPOINT,
                access_key=settings.B2_KEY_ID,
                secret_key=settings.B2_APPLICATION_KEY,
                bucket=settings.B2_BUCKET,
                secure=True,
                provider="b2",
            )
        else:
            _default_client = S3StorageClient(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                bucket=settings.MINIO_BUCKET,
                secure=settings.MINIO_USE_SSL,
                provider="minio",
            )
    
    return _default_client


def reset_storage_client():
    """Reset the default client (useful for testing or config changes)."""
    global _default_client
    _default_client = None
