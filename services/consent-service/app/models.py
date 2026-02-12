import datetime
import uuid

from sqlalchemy import JSON, Column, DateTime, String

from .database import Base


class Consent(Base):
    __tablename__ = "consents"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    connection_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True, default="active")
    provider = Column(String, nullable=False)
    scopes = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
    )

