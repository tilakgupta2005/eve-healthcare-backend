from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentOut, WebhookPayload
from app.services.booking_service import ensure_owner_or_admin, get_booking_or_404
from app.services.payment_service import create_payment_attempt, process_webhook_event

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def pay_for_booking(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simulates a synchronous payment-gateway charge for a booking: resolves
    to SUCCESS or FAILED and updates the booking's status accordingly.
    """
    booking = get_booking_or_404(db, payload.booking_id)
    ensure_owner_or_admin(booking, current_user)
    return create_payment_attempt(db, booking, force_status=payload.force_status)


@router.post("/webhook/", status_code=status.HTTP_200_OK)
def payment_webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    """
    Receives asynchronous payment-status notifications from the (simulated)
    payment provider. Intentionally has no auth dependency, matching how a
    real provider calls your webhook directly -- in production this would
    instead be protected by verifying the provider's request signature.

    Guaranteed idempotent: replaying the same event_id any number of times
    has the same effect as calling it once.
    """
    return process_webhook_event(db, payload)
