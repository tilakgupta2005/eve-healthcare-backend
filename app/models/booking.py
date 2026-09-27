import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.db_types import GUID


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"      # created, awaiting payment
    CONFIRMED = "CONFIRMED"  # payment succeeded
    FAILED = "FAILED"        # payment failed
    CANCELLED = "CANCELLED"  # cancelled by the user before confirmation


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    test_id = Column(GUID(), ForeignKey("diagnostic_tests.id"), nullable=False)
    centre_id = Column(GUID(), ForeignKey("diagnostic_centres.id"), nullable=False)

    appointment_time = Column(DateTime(timezone=True), nullable=False)

    # Snapshot of the test's price at booking time, so a later price change
    # at the centre doesn't retroactively alter what an existing booking owes.
    amount = Column(Numeric(10, 2), nullable=False)

    status = Column(
        Enum(BookingStatus, name="booking_status"),
        default=BookingStatus.PENDING,
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="bookings")
    test = relationship("DiagnosticTest")
    centre = relationship("DiagnosticCentre")
    payments = relationship("Payment", back_populates="booking")
