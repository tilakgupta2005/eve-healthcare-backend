"""
Business logic for creating and managing bookings, kept out of the router
layer so routers stay thin (HTTP concerns only) and this logic is easy to
unit test directly.
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.schemas.booking import BookingCreate


def create_booking(db: Session, user_id: uuid.UUID, payload: BookingCreate) -> Booking:
    centre = db.get(DiagnosticCentre, payload.centre_id)
    if centre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diagnostic centre not found.")

    test = db.get(DiagnosticTest, payload.test_id)
    if test is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diagnostic test not found.")

    if test.centre_id != centre.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "That test is not offered at the specified centre.",
        )

    appointment_time = payload.appointment_time
    if appointment_time.tzinfo is None:
        appointment_time = appointment_time.replace(tzinfo=timezone.utc)
    if appointment_time <= datetime.now(timezone.utc):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "appointment_time must be in the future."
        )

    booking = Booking(
        user_id=user_id,
        test_id=test.id,
        centre_id=centre.id,
        appointment_time=appointment_time,
        amount=test.price,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found.")
    return booking


def ensure_owner_or_admin(booking: Booking, current_user) -> None:
    if booking.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You do not have permission to access this booking.",
        )


def cancel_booking(db: Session, booking: Booking) -> Booking:
    if booking.status == BookingStatus.CONFIRMED:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A confirmed (paid) booking cannot be cancelled through this endpoint.",
        )
    if booking.status == BookingStatus.CANCELLED:
        # Idempotent no-op rather than an error: cancelling twice is harmless.
        return booking

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking
