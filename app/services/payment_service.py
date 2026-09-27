"""
Business logic for the simulated payment flow:

  1. `create_payment_attempt` — POST /payments/ synchronously "charges" a
     booking (like a real gateway's synchronous confirm call) and updates
     the booking immediately.
  2. `process_webhook_event` — POST /payments/webhook/ is the *asynchronous*
     channel a real provider also uses to notify us of a payment's status
     (confirmations, delayed settlement, retried delivery, etc). It must be
     safe to call any number of times with the same event_id.
"""
import random
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus, WebhookEvent
from app.schemas.payment import WebhookPayload


def create_payment_attempt(
    db: Session, booking: Booking, force_status: PaymentStatus | None = None
) -> Payment:
    if booking.status == BookingStatus.CONFIRMED:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "This booking has already been paid for."
        )
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot pay for a cancelled booking."
        )

    if force_status is not None:
        outcome = force_status
    else:
        outcome = (
            PaymentStatus.SUCCESS
            if random.random() < settings.payment_success_rate
            else PaymentStatus.FAILED
        )

    payment = Payment(
        booking_id=booking.id,
        provider_transaction_id=f"txn_{uuid.uuid4().hex}",
        amount=booking.amount,
        status=outcome,
    )
    db.add(payment)

    booking.status = (
        BookingStatus.CONFIRMED if outcome == PaymentStatus.SUCCESS else BookingStatus.FAILED
    )

    db.commit()
    db.refresh(payment)
    return payment


def process_webhook_event(db: Session, payload: WebhookPayload) -> dict:
    # --- Fast-path idempotency check ---
    already = db.query(WebhookEvent).filter_by(event_id=payload.event_id).first()
    if already is not None:
        return {"status": "already_processed", "event_id": payload.event_id}

    payment = (
        db.query(Payment)
        .filter_by(provider_transaction_id=payload.provider_transaction_id)
        .first()
    )
    if payment is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No payment found for the given provider_transaction_id.",
        )

    # Record the event *before* mutating state, inside the same transaction.
    # If two copies of the same webhook race each other, the unique
    # constraint on event_id makes the loser's flush fail here -- before it
    # has touched payment/booking state -- so we can safely treat it as an
    # already-processed duplicate instead of double-applying the update.
    db.add(WebhookEvent(event_id=payload.event_id, payload=payload.model_dump(mode="json")))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"status": "already_processed", "event_id": payload.event_id}

    payment.status = payload.status

    booking: Booking = payment.booking
    # A user-cancelled booking is left alone: a late/duplicate provider
    # notification should not silently resurrect a cancelled booking.
    if booking.status != BookingStatus.CANCELLED:
        if payload.status == PaymentStatus.SUCCESS:
            booking.status = BookingStatus.CONFIRMED
        elif payload.status == PaymentStatus.FAILED:
            booking.status = BookingStatus.FAILED

    db.commit()
    return {
        "status": "processed",
        "event_id": payload.event_id,
        "booking_status": booking.status,
    }
