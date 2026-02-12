import uuid

from sqlalchemy import JSON, Column, String

from .database import Base


class Partner(Base):
    __tablename__ = "partners"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)
    services_offered = Column(JSON, nullable=False)
    website = Column(String, nullable=False)

