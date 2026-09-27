"""
Import every model module so that `Base.metadata.create_all(...)` (called
from app.main on startup) knows about all tables, and so relationship()
string references resolve correctly.
"""
from app.models.user import User            # noqa: F401
from app.models.centre import DiagnosticCentre  # noqa: F401
from app.models.test import DiagnosticTest      # noqa: F401
from app.models.booking import Booking, BookingStatus  # noqa: F401
from app.models.payment import Payment, PaymentStatus, WebhookEvent  # noqa: F401
