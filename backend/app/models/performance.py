"""
Performance models for PageSpeed Insights data.

Stores Core Web Vitals and performance metrics for site pages.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class PerformanceSnapshot(Base, BaseModel):
    """
    PageSpeed Insights analysis snapshot.

    Stores performance metrics, Core Web Vitals, and optimization opportunities
    for a specific URL at a point in time.
    """

    __tablename__ = "performance_snapshots"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    audit_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audit_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Page identification
    url = Column(String(2048), nullable=False, index=True)
    template_type = Column(String(50), nullable=True, index=True)
    strategy = Column(String(10), nullable=False)  # mobile, desktop

    # Overall score (0-100)
    performance_score = Column(Integer, nullable=True)

    # Core Web Vitals - Lab Data (milliseconds except CLS which is ratio)
    lcp_ms = Column(Integer, nullable=True)       # Largest Contentful Paint
    fid_ms = Column(Integer, nullable=True)       # First Input Delay (from field data)
    cls = Column(Float, nullable=True)            # Cumulative Layout Shift
    fcp_ms = Column(Integer, nullable=True)       # First Contentful Paint
    ttfb_ms = Column(Integer, nullable=True)      # Time to First Byte
    tbt_ms = Column(Integer, nullable=True)       # Total Blocking Time
    speed_index_ms = Column(Integer, nullable=True)  # Speed Index
    tti_ms = Column(Integer, nullable=True)       # Time to Interactive
    inp_ms = Column(Integer, nullable=True)       # Interaction to Next Paint (from field data)

    # Overall CWV status: good, needs_improvement, poor
    cwv_status = Column(String(20), nullable=True)

    # Raw data storage
    opportunities = Column(JSONB, default=list)    # Optimization opportunities
    diagnostics = Column(JSONB, default=dict)      # Diagnostic details
    field_data = Column(JSONB, default=dict)       # CrUX field data if available

    # Timestamp
    checked_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    site = relationship("Site", back_populates="performance_snapshots")

    def __repr__(self) -> str:
        return f"<PerformanceSnapshot {self.url[:50]}... score={self.performance_score}>"

    @property
    def lcp_status(self) -> str:
        """Get LCP status based on thresholds."""
        if self.lcp_ms is None:
            return "unknown"
        if self.lcp_ms <= 2500:
            return "good"
        elif self.lcp_ms <= 4000:
            return "needs_improvement"
        return "poor"

    @property
    def cls_status(self) -> str:
        """Get CLS status based on thresholds."""
        if self.cls is None:
            return "unknown"
        if self.cls <= 0.1:
            return "good"
        elif self.cls <= 0.25:
            return "needs_improvement"
        return "poor"

    @property
    def fcp_status(self) -> str:
        """Get FCP status based on thresholds."""
        if self.fcp_ms is None:
            return "unknown"
        if self.fcp_ms <= 1800:
            return "good"
        elif self.fcp_ms <= 3000:
            return "needs_improvement"
        return "poor"
