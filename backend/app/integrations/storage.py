"""
Storage Integration Client

Provides S3-compatible storage operations using MinIO.
Used for storing crawl data, reports, exports, and other files.
"""

import io
import json
from typing import Optional, List, Dict, Any, BinaryIO, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import mimetypes

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import CopySource

from app.config import settings


@dataclass
class StorageConfig:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    secure: bool = False


@dataclass
class StorageObject:
    key: str
    size: int
    last_modified: datetime
    etag: str
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class StorageClient:
    """S3-compatible storage client using MinIO."""
    
    def __init__(self, config: Optional[StorageConfig] = None):
        if config is None:
            config = StorageConfig(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                bucket=settings.MINIO_BUCKET,
                secure=settings.MINIO_USE_SSL,
            )
        self.config = config
        self._client = Minio(
            config.endpoint,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.secure,
        )
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure the bucket exists, create if not."""
        try:
            if not self._client.bucket_exists(self.config.bucket):
                self._client.make_bucket(self.config.bucket)
        except S3Error as e:
            # Bucket might already exist or we don't have permissions
            if e.code != "BucketAlreadyOwnedByYou":
                raise
    
    def _get_content_type(self, key: str) -> str:
        """Guess content type from file extension."""
        content_type, _ = mimetypes.guess_type(key)
        return content_type or "application/octet-stream"
    
    def upload_file(
        self,
        key: str,
        file_path: Union[str, Path],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload a file from disk."""
        file_path = Path(file_path)
        
        if content_type is None:
            content_type = self._get_content_type(str(file_path))
        
        self._client.fput_object(
            self.config.bucket,
            key,
            str(file_path),
            content_type=content_type,
            metadata=metadata,
        )
        
        return key
    
    def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload bytes directly."""
        if content_type is None:
            content_type = self._get_content_type(key)
        
        stream = io.BytesIO(data)
        
        self._client.put_object(
            self.config.bucket,
            key,
            stream,
            length=len(data),
            content_type=content_type,
            metadata=metadata,
        )
        
        return key
    
    def upload_json(
        self,
        key: str,
        data: Any,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload JSON data."""
        json_bytes = json.dumps(data, indent=2, default=str).encode("utf-8")
        return self.upload_bytes(
            key,
            json_bytes,
            content_type="application/json",
            metadata=metadata,
        )
    
    def upload_stream(
        self,
        key: str,
        stream: BinaryIO,
        length: int,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload from a stream."""
        if content_type is None:
            content_type = self._get_content_type(key)
        
        self._client.put_object(
            self.config.bucket,
            key,
            stream,
            length=length,
            content_type=content_type,
            metadata=metadata,
        )
        
        return key
    
    def download_file(
        self,
        key: str,
        file_path: Union[str, Path],
    ) -> Path:
        """Download a file to disk."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._client.fget_object(
            self.config.bucket,
            key,
            str(file_path),
        )
        
        return file_path
    
    def download_bytes(self, key: str) -> bytes:
        """Download file as bytes."""
        response = self._client.get_object(self.config.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    
    def download_json(self, key: str) -> Any:
        """Download and parse JSON file."""
        data = self.download_bytes(key)
        return json.loads(data.decode("utf-8"))
    
    def download_stream(self, key: str) -> BinaryIO:
        """Get a stream to download file."""
        response = self._client.get_object(self.config.bucket, key)
        return response
    
    def delete(self, key: str) -> bool:
        """Delete an object."""
        try:
            self._client.remove_object(self.config.bucket, key)
            return True
        except S3Error:
            return False
    
    def delete_many(self, keys: List[str]) -> int:
        """Delete multiple objects. Returns count of deleted."""
        from minio.deleteobjects import DeleteObject
        
        delete_objects = [DeleteObject(key) for key in keys]
        errors = list(self._client.remove_objects(self.config.bucket, delete_objects))
        
        return len(keys) - len(errors)
    
    def delete_prefix(self, prefix: str) -> int:
        """Delete all objects with given prefix."""
        objects = self.list_objects(prefix=prefix)
        keys = [obj.key for obj in objects]
        
        if not keys:
            return 0
        
        return self.delete_many(keys)
    
    def exists(self, key: str) -> bool:
        """Check if an object exists."""
        try:
            self._client.stat_object(self.config.bucket, key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise
    
    def get_info(self, key: str) -> Optional[StorageObject]:
        """Get object metadata."""
        try:
            stat = self._client.stat_object(self.config.bucket, key)
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
    
    def list_objects(
        self,
        prefix: str = "",
        recursive: bool = True,
        max_keys: Optional[int] = None,
    ) -> List[StorageObject]:
        """List objects with optional prefix filter."""
        objects = []
        
        for obj in self._client.list_objects(
            self.config.bucket,
            prefix=prefix,
            recursive=recursive,
        ):
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
    
    def copy(
        self,
        source_key: str,
        dest_key: str,
        source_bucket: Optional[str] = None,
    ) -> str:
        """Copy an object."""
        source_bucket = source_bucket or self.config.bucket
        
        self._client.copy_object(
            self.config.bucket,
            dest_key,
            CopySource(source_bucket, source_key),
        )
        
        return dest_key
    
    def move(
        self,
        source_key: str,
        dest_key: str,
    ) -> str:
        """Move an object (copy + delete)."""
        self.copy(source_key, dest_key)
        self.delete(source_key)
        return dest_key
    
    def get_presigned_url(
        self,
        key: str,
        expires: timedelta = timedelta(hours=1),
        method: str = "GET",
    ) -> str:
        """Generate a presigned URL for temporary access."""
        if method == "GET":
            return self._client.presigned_get_object(
                self.config.bucket,
                key,
                expires=expires,
            )
        elif method == "PUT":
            return self._client.presigned_put_object(
                self.config.bucket,
                key,
                expires=expires,
            )
        else:
            raise ValueError(f"Unsupported method: {method}")
    
    def get_public_url(self, key: str) -> str:
        """Get the public URL (requires bucket to be public)."""
        protocol = "https" if self.config.secure else "http"
        return f"{protocol}://{self.config.endpoint}/{self.config.bucket}/{key}"


# Storage path helpers for SEOman

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


# Default client instance
_default_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    """Get or create the default storage client."""
    global _default_client
    if _default_client is None:
        _default_client = StorageClient()
    return _default_client
