"""
Authentication schemas.
"""
from uuid import UUID

from pydantic import EmailStr, Field

from app.models.user import UserRole, UserStatus
from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


class LoginRequest(BaseSchema):
    """Login request schema."""
    
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseSchema):
    """Registration request schema."""
    
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=2, max_length=255)
    tenant_name: str | None = Field(default=None, min_length=2, max_length=255)


class TokenResponse(BaseSchema):
    """Token response schema."""
    
    access_token: str
    token_type: str = "bearer"


class UserResponse(IDSchema, TimestampSchema):
    """User response schema."""
    
    email: str
    name: str
    role: UserRole
    status: UserStatus
    tenant_id: UUID | None = None


class AuthResponse(TokenResponse):
    """Authentication response with user info."""
    
    user: UserResponse


class UserUpdate(BaseSchema):
    """User update schema."""
    
    name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
