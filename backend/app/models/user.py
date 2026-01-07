"""
User model with role-based access control.
"""
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class UserRole(str, PyEnum):
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    SEO_MANAGER = "seo_manager"
    READ_ONLY = "read_only"


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class User(Base, BaseModel):
    """User model with authentication and role information."""
    
    __tablename__ = "users"
    
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,  # Nullable for super_admin
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole),
        default=UserRole.READ_ONLY,
        nullable=False,
    )
    status = Column(
        Enum(UserStatus),
        default=UserStatus.ACTIVE,
        nullable=False,
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    
    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
    
    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN
    
    @property
    def is_tenant_admin(self) -> bool:
        return self.role in (UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN)
    
    def can_manage_tenant(self, tenant_id: str) -> bool:
        """Check if user can manage the given tenant."""
        if self.is_super_admin:
            return True
        return str(self.tenant_id) == str(tenant_id)
