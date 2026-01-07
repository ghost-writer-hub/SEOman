"""
Security utilities for authentication and authorization.
"""
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# Permission definitions
PERMISSIONS = {
    "super_admin": [
        "tenant:create", "tenant:read", "tenant:update", "tenant:delete",
        "user:create", "user:read", "user:update", "user:delete",
        "site:create", "site:read", "site:update", "site:delete",
        "audit:create", "audit:read",
        "keyword:create", "keyword:read",
        "plan:create", "plan:read", "plan:update",
        "content:create", "content:read", "content:update", "content:delete",
        "settings:read", "settings:update",
    ],
    "tenant_admin": [
        "user:create", "user:read", "user:update",
        "site:create", "site:read", "site:update", "site:delete",
        "audit:create", "audit:read",
        "keyword:create", "keyword:read",
        "plan:create", "plan:read", "plan:update",
        "content:create", "content:read", "content:update", "content:delete",
    ],
    "seo_manager": [
        "site:read",
        "audit:create", "audit:read",
        "keyword:create", "keyword:read",
        "plan:create", "plan:read", "plan:update",
        "content:create", "content:read", "content:update",
    ],
    "read_only": [
        "site:read",
        "audit:read",
        "keyword:read",
        "plan:read",
        "content:read",
    ],
}


def check_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    role_permissions = PERMISSIONS.get(role, [])
    return permission in role_permissions
