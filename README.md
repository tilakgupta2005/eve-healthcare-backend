# EVE Healthcare — Diagnostics Booking & Payments API

A backend service for browsing diagnostic centres/tests, booking a test, and
paying for it through a simulated (idempotent) payment gateway. Built for
the EVE Healthcare SDE Intern assignment.

**Stack:** FastAPI + SQLAlchemy 2.0 + PostgreSQL (SQLite for quick local
runs) + JWT auth + pytest.

---

## 1. Project structure

```
app/
├── main.py                 # FastAPI app: wiring, CORS, startup, /health
├── config.py                # Settings (env-var driven)
├── database.py               # Engine / session / get_db dependency
├── db_types.py                # Cross-dialect GUID column type (Postgres UUID / SQLite CHAR32)
│
├── models/                  # SQLAlchemy ORM models (one file per entity)
│   ├── user.py                 # User
│   ├── centre.py                # DiagnosticCentre
│   ├── test.py                   # DiagnosticTest (belongs to a centre, has its own price)
│   ├── booking.py                # Booking + BookingStatus enum
│   └── payment.py                 # Payment + PaymentStatus enum + WebhookEvent (idempotency log)
│
├── schemas/                 # Pydantic request/response models, mirrors models/
│   ├── user.py, centre.py, test.py, booking.py, payment.py
│
├── core/                    # Cross-cutting concerns
│   ├── security.py             # password hashing, JWT create/decode
│   └── deps.py                   # get_current_user / get_current_admin_user
│
├── services/                # Business logic (routers stay thin, this is unit-testable)
│   ├── booking_service.py      # create/cancel booking, ownership checks
│   └── payment_service.py       # simulate a charge, process a webhook idempotently
│
└── routers/                 # HTTP layer — one file per resource
    ├── auth.py                    # /auth/signup, /auth/login
    ├── centres.py                  # /centres/... (+ nested tests)
    ├── tests.py                     # /tests/... (browse across centres)
    ├── bookings.py                   # /bookings/...
    └── payments.py                    # /payments/, /payments/webhook/

tests/
├── conftest.py               # in-memory SQLite DB per test, auth/user/centre fixtures
├── test_auth.py
├── test_centres.py
├── test_bookings.py
├── test_payments.py
└── test_webhook.py             # idempotency is specifically exercised here
```

**Why this layout:** each request flows `router → service → model`. Routers
only handle HTTP concerns (status codes, request/response shapes); all
actual business rules (ownership checks, status transitions, idempotency)
live in `services/`, so they can be tested directly and reused without
going through the HTTP layer.

---

## 2. Running it locally

### Option A — Docker (recommended, uses Postgres)

```bash
docker-compose up --build
```

The API will be at `http://localhost:8000`. Interactive docs (Swagger UI)
at `http://localhost:8000/docs`.

### Option B — Local Python + SQLite (fastest to get running)

```bash
python -m venv .venv
source .venv/scripts/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # defaults already point at a local SQLite file
uvicorn app.main:app --reload
```

### Running tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests run fully in-memory (SQLite) and don't touch whatever `DATABASE_URL`
is set to — see `tests/conftest.py`.

---

## 3. Database / schema design

```
User (1) ───< Booking >─── (1) DiagnosticTest ───> (1) DiagnosticCentre
                │                                          │
                └──────────────< belongs to >───────────────┘
Booking (1) ───< Payment
WebhookEvent  (standalone idempotency log, keyed by event_id)
```

* **User** — email/password (bcrypt-hashed) + `is_admin` flag. Admins can
  manage centres/tests; regular users book and pay.
* **DiagnosticCentre** — name + location.
* **DiagnosticTest** — belongs to exactly one centre, has its own `price`.
  (Modelled per-centre rather than a global test catalogue, since the
  assignment lists "test price" as an attribute of a centre's offering —
  the same test name can plausibly cost different amounts at different
  centres in real life.)
* **Booking** — links a user to a (test, centre) pair, with an
  `appointment_time` and a `status`
  (`PENDING → CONFIRMED | FAILED | CANCELLED`). `amount` is a **snapshot**
  of the test's price at booking time, so a later price change at the
  centre never retroactively changes what an existing booking owes.
* **Payment** — one row per payment *attempt* on a booking (a booking can
  have more than one attempt if an earlier one failed). Has a unique
  `provider_transaction_id`, the handle a webhook uses to find it again.
* **WebhookEvent** — every successfully-processed webhook event, keyed by
  the provider's `event_id`. This table *is* the idempotency mechanism
  (see §5).

All primary keys are UUIDs. A small `GUID` `TypeDecorator`
(`app/db_types.py`) stores them as a native `UUID` column on Postgres and
as a 32-char hex string on SQLite, so the same models work unmodified
against both — no migration surprises moving from local dev to the
docker-compose Postgres setup.

Tables are created via `Base.metadata.create_all()` at startup, which is
enough for this assignment's scope; see §7 for what I'd change for a real
production service.

---

## 4. API reference

Full interactive docs with request/response schemas: `/docs` (Swagger) or
`/redoc`. Below are the highlights with example requests.

### Auth

```bash
# Sign up
curl -X POST localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "alex@example.com", "password": "password123", "full_name": "Alex"}'

# Log in (OAuth2 password flow: form-encoded, field is "username")
curl -X POST localhost:8000/auth/login \
  -d "username=alex@example.com&password=password123"
# -> {"access_token": "<jwt>", "token_type": "bearer"}
```

Every authenticated request below needs `Authorization: Bearer <jwt>`.

> There's no signup flag for `is_admin` (a signup endpoint that lets you
> self-declare as admin would be a real security hole). For grading /
> local testing, flip a user's `is_admin` column directly in the DB, or
> seed one via a Python shell (`from app.models.user import User` ...).

### Centres & tests

```bash
# Public: browse
curl localhost:8000/centres/?location=Indore
curl localhost:8000/centres/<centre_id>/tests
curl localhost:8000/tests/?name=blood

# Admin only: onboard a centre and add a test to it
curl -X POST localhost:8000/centres/ -H "Authorization: Bearer <admin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "City Diagnostics", "location": "Indore"}'

curl -X POST localhost:8000/centres/<centre_id>/tests -H "Authorization: Bearer <admin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Complete Blood Count", "price": "499.00"}'
```

### Bookings

```bash
curl -X POST localhost:8000/bookings/ -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"test_id": "<test_id>", "centre_id": "<centre_id>", "appointment_time": "2026-10-05T10:00:00Z"}'

curl localhost:8000/bookings/ -H "Authorization: Bearer <jwt>"          # your own bookings
curl localhost:8000/bookings/<booking_id> -H "Authorization: Bearer <jwt>"
curl -X POST localhost:8000/bookings/<booking_id>/cancel -H "Authorization: Bearer <jwt>"
```

### Payments

```bash
# Simulated synchronous charge — resolves to SUCCESS or FAILED immediately
# and updates the booking. Omit force_status for a random outcome
# (weighted by PAYMENT_SUCCESS_RATE); pass it to get a deterministic result.
curl -X POST localhost:8000/payments/ -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"booking_id": "<booking_id>", "force_status": "SUCCESS"}'

# Webhook — simulates the provider's async notification channel.
# No auth (a real provider calls this directly); safe to POST repeatedly
# with the same event_id.
curl -X POST localhost:8000/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"event_id": "evt_123", "provider_transaction_id": "txn_abc", "status": "SUCCESS"}'
```

---

## 5. How idempotency works (webhook)

`POST /payments/webhook/` is guaranteed safe to call any number of times
with the same `event_id`:

1. **Fast path:** look up `event_id` in `webhook_events`. If it's already
   there, return `{"status": "already_processed"}` immediately — no state
   is touched.
2. **Race-safety:** if two copies of the *same* event arrive concurrently
   and both pass the check above before either commits, the event row is
   inserted (and `db.flush()`'d) *before* any payment/booking mutation
   happens. The table's `UNIQUE` constraint on `event_id` means the loser
   of the race gets an `IntegrityError` at that flush — caught, rolled
   back, and treated as `already_processed` — rather than double-applying
   the booking-status change.
3. Only after the event is durably recorded do we update the `Payment` row
   and transition the `Booking` (`SUCCESS → CONFIRMED`,
   `FAILED → FAILED`). A booking the user already `CANCELLED` is left
   alone — a late or duplicate provider notification can't resurrect it.

This is exercised directly in `tests/test_webhook.py` (`test_duplicate_
webhook_event_is_idempotent`, `test_webhook_does_not_resurrect_cancelled_
booking`).

---

## 6. Edge cases handled

| Case | Behaviour |
|---|---|
| Invalid JSON body / missing fields | `422`, FastAPI/Pydantic validation |
| Malformed UUID in a path param | `422` (FastAPI's own path-type validation) |
| Unknown booking / centre / test id | `404` |
| Booking a test not offered at the given centre | `400` |
| Booking with a past `appointment_time` | `400` |
| Viewing/cancelling/paying someone else's booking | `403` |
| Paying a booking that's already `CONFIRMED` | `400` (no double payment) |
| Paying a `CANCELLED` booking | `400` |
| Cancelling an already-`CANCELLED` booking | `200`, no-op (idempotent) |
| Cancelling a `CONFIRMED` (paid) booking | `400` |
| Repeated webhook delivery (same `event_id`) | `200`, no duplicate side effects |
| Webhook for an unknown `provider_transaction_id` | `404` |
| Non-admin creating a centre/test | `403` |
| Wrong password / unknown user at login | `401` |
| Duplicate signup email | `400` |
| Missing/expired/garbage JWT on a protected route | `401` |

---

## 7. Assumptions

- `is_admin` is a plain boolean flag on `User` rather than a separate roles
  system — enough to gate centre/test management for this assignment.
- A `DiagnosticTest` belongs to one centre (price is per centre-test pair),
  not a shared global catalogue — see §3 for reasoning.
- `POST /payments/` simulates a **synchronous** gateway charge (result
  known immediately, booking updated in the same request) with an
  optional `force_status` for deterministic testing. The webhook is a
  separate, genuinely asynchronous channel — realistic in that real
  providers (e.g. Stripe) often do both: a synchronous confirm call *and*
  a webhook for the same event, used for reconciliation/retries.
- The webhook endpoint has no authentication — it's meant to represent an
  inbound call from an external provider. In production this would be
  protected with a signature-verification step (see below).
- Schema is created via `create_all()` at startup rather than migrations —
  fine for this exercise, not for production.

## 8. What I'd improve with more time

- **Alembic migrations** instead of `create_all()`, for real schema
  evolution and to keep `create_all()`'s side effect out of the test run.
- **Webhook signature verification** (HMAC secret shared with the
  "provider") instead of an open endpoint.
- **Rate limiting** on `/auth/login` and `/payments/` to blunt brute-force
  and payment-spam attempts.
- **Structured logging** (request id, user id) instead of default
  Uvicorn access logs, for real debuggability in production.
- **Pagination** on `GET /centres/`, `/tests/`, `/bookings/` (currently a
  simple `skip`/`limit`; would move to cursor-based pagination at scale).
- **Background retry handling** for the payment webhook path (a small
  queue/worker re-delivering failed outbound notifications, if this
  service were the one calling *out* to a provider instead of receiving
  from it).
- **Docker healthcheck** for the `app` service itself (currently only `db`
  has one) and a non-root user in the image.
