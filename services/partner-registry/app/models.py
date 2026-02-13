import datetime
import uuid

from sqlalchemy import CheckConstraint, JSON, Column, DateTime, ForeignKey, Index, String

from .database import Base


class Partner(Base):
    __tablename__ = "partners"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)
    services_offered = Column(JSON, nullable=False)
    website = Column(String, nullable=False)


class HandoffLead(Base):
    __tablename__ = "handoff_leads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('initiated', 'qualified', 'rejected', 'converted')",
            name="ck_handoff_leads_status_allowed",
        ),
        Index("ix_handoff_leads_status", "status"),
        Index("ix_handoff_leads_partner_created_at", "partner_id", "created_at"),
        Index("ix_handoff_leads_user_partner_created_at", "user_id", "partner_id", "created_at"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    partner_id = Column(String, ForeignKey("partners.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="initiated")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
    )

