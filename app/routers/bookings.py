import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingOut
from app.services.booking_service import (
    cancel_booking,
    create_booking,
    ensure_owner_or_admin,
    get_booking_or_404,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def book_test(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_booking(db, current_user.id, payload)


@router.get("/", response_model=list[BookingOut])
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Authenticated users see only their own bookings. Admins may pass
    ?all=true to see every booking (e.g. for support/ops purposes).
    """
    query = db.query(Booking)
    if not current_user.is_admin:
        query = query.filter(Booking.user_id == current_user.id)
    return query.order_by(Booking.created_at.desc()).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = get_booking_or_404(db, booking_id)
    ensure_owner_or_admin(booking, current_user)
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_my_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = get_booking_or_404(db, booking_id)
    ensure_owner_or_admin(booking, current_user)
    return cancel_booking(db, booking)
