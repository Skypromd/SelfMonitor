import datetime
import uuid

from sqlalchemy import JSON, Column, DateTime, String

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

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    partner_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="initiated")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        index=True,
    )

