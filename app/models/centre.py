import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.db_types import GUID


class DiagnosticCentre(Base):
    __tablename__ = "diagnostic_centres"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tests = relationship(
        "DiagnosticTest", back_populates="centre", cascade="all, delete-orphan"
    )
