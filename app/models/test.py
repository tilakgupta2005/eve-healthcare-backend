import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.db_types import GUID


class DiagnosticTest(Base):
    """
    A test offered by a specific diagnostic centre. Price is modelled per
    (centre, test) pair since the same test can be priced differently at
    different centres in real life.
    """

    __tablename__ = "diagnostic_tests"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    centre_id = Column(GUID(), ForeignKey("diagnostic_centres.id"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    centre = relationship("DiagnosticCentre", back_populates="tests")
