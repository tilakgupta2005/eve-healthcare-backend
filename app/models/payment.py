import enum
import uuid

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.db_types import GUID


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Payment(Base):
    """
    One row per payment *attempt* against a booking. A booking can have more
    than one attempt (e.g. first attempt fails, user retries), but only ever
    at most one attempt that resolves to SUCCESS in the normal flow.
    """

    __tablename__ = "payments"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    booking_id = Column(GUID(), ForeignKey("bookings.id"), nullable=False, index=True)

    # Stand-in for whatever ID a real payment gateway would give us back.
    # Unique so we can safely look a payment up from a webhook call.
    provider_transaction_id = Column(String(64), unique=True, nullable=False, index=True)

    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        Enum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.PENDING,
        nullable=False,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    booking = relationship("Booking", back_populates="payments")


class WebhookEvent(Base):
    """
    Log of every payment-webhook event we have successfully processed,
    keyed by the provider's own event id. This is the source of truth for
    idempotency: before acting on an incoming webhook we check whether its
    event_id is already here, and if so we no-op and return success without
    touching booking/payment state again.
    """

    __tablename__ = "webhook_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(128), unique=True, nullable=False, index=True)
    payload = Column(JSON, nullable=True)

    received_at = Column(DateTime(timezone=True), server_default=func.now())
