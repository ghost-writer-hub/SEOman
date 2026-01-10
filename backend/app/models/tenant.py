"""
Tenant model for multi-tenancy.
"""
from enum import Enum as PyEnum

from sqlalchemy import Column, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class TenantStatus(str, PyEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Tenant(Base, BaseModel):
    """Tenant model representing an organization."""
    
    __tablename__ = "tenants"
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(
        Enum(TenantStatus),
        default=TenantStatus.ACTIVE,
        nullable=False,
    )
    plan = Column(String(50), default="free")
    settings = Column(JSONB, default=dict)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    sites = relationship("Site", back_populates="tenant", cascade="all, delete-orphan")
    usage_records = relationship("TenantUsage", back_populates="tenant", cascade="all, delete-orphan")
    quota = relationship("TenantQuota", back_populates="tenant", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant {self.name} ({self.slug})>"
