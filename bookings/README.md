# Habot LSA Booking

**Candidate:** Akshita Chadha
**Contact:** akshitachadha01@gmail.com
**Position Applied For:** Python Backend Developer — HabotConnect

---

A backend service for booking Learning Support Assistants (LSAs), built with Django and Django REST Framework. The project models a real booking workflow: searching for available LSAs, creating time-bound bookings, and confirming them through a payment webhook — with concurrency safety and data integrity enforced at the database and transaction level throughout.

## Overview

The system supports the following flow:

1. Parents search for LSAs by skill and requested time window.
2. A parent creates a booking for a specific LSA and time range. The booking starts in `PENDING_PAYMENT`, after which the service initiates a payment request through the mock payment gateway.
3. A payment webhook (`payment.success` / `payment.failed`) confirms or fails the booking.
4. Overlapping bookings for the same LSA are rejected; concurrent booking attempts are protected against race conditions with row-level locking.

The implementation favors **data integrity, transactional safety, and defensive server-side validation** over broad feature scope — booking status can never be set directly by a client, overlap checks are enforced under lock, and payment webhooks are idempotent by transaction ID.

## Tech Stack

| Component | Choice |
|---|---|
| Language | Python 3.13 |
| Framework | Django 6.1 |
| API | Django REST Framework 3.18 |
| Database | PostgreSQL (via `psycopg` 3) |
| External calls | `requests` |
| Testing | Django's test runner with `pytest` / `pytest-django` available |
| CI | GitHub Actions |
| Config | `python-dotenv` |

## Design Pattern: MVT vs. MVC

Django follows **MVT (Model-View-Template)** rather than the classical **MVC (Model-View-Controller)** pattern used by frameworks like Flask. The mapping between the two:

| MVC | Django's MVT | Role in this project |
|---|---|---|
| Model | Model | `bookings/models.py` — `Parent`, `Skill`, `LSAProfile`, `Booking`, `Payment` |
| Controller | View | `bookings/views.py` — receives the request, delegates to serializers/services, returns a `Response` |
| View | Template | Not used — this is a pure JSON API with no server-rendered HTML |

The practical difference is that in MVT, **Django itself acts as the controller** (URL routing + the request/response cycle), so the "View" classes here (`BookingCreateView`, `LSASearchView`, `PaymentWebhookView`) are closer to MVC's *controllers* than to MVC's *views* — they don't render presentation, they orchestrate.

This project pushes the split further than a typical MVT app by pulling business logic **out of the views entirely** and into a dedicated **service layer** (`services.py`, `payment_service.py`):

- **Serializers** (`serializers.py`) handle input validation and shape.
- **Views** handle HTTP concerns only — status codes, request/response wiring.
- **Services** own the business-critical logic: transactional booking creation, locking, conflict detection, and payment state transitions.

This keeps the parts of the system most likely to contain bugs (concurrency, state transitions, data integrity) independently testable and decoupled from the web framework, rather than living inside `views.py` as is common in smaller MVT apps.

## Project Structure

```
habot-lsa-booking/
├── bookings/
│   ├── models.py            # Parent, Skill, LSAProfile, Booking, Payment
│   ├── serializers.py       # Request validation + write-through to services
│   ├── views.py             # BookingCreateView, LSASearchView, PaymentWebhookView
│   ├── services.py          # create_booking() — transactional booking logic
│   ├── payment_service.py   # process_payment_webhook() — payment state machine
│   ├── external_services.py # create_payment() — mock payment gateway integration
│   ├── debug_views.py       # N+1 query demonstration endpoint
│   ├── exceptions.py        # BookingConflictError
│   ├── urls.py               # App-level routes
│   └── tests/
│       ├── test_bookings.py
│       ├── test_search.py
│       ├── test_payments.py
│       └── test_external_services.py
├── config/
│   ├── settings.py
│   ├── urls.py               # Project-level routes
│   ├── wsgi.py / asgi.py
├── .github/workflows/tests.yaml
├── manage.py
├── requirements.txt
└── .gitignore
```

## Data Model

```
Parent ──< Booking >── LSAProfile ──< Skill (M2M)
              │
              └── 1:1 ── Payment
```

**Parent** — `name`, `email` (unique), `phone`, `created_at`.

**Skill** — `name` (unique).

**LSAProfile** — `name`, `email` (unique), `bio`, `is_active`, `skills` (M2M → Skill), `created_at`.

**Booking** — the central entity, linking `parent`, `lsa`, `start_time`, `end_time`, and a controlled `status` (`TextChoices`: `PENDING_PAYMENT`, `CONFIRMED`, `PAYMENT_FAILED`, `CANCELLED`, `COMPLETED`), plus `created_at` / `updated_at`.

**Payment** — one-to-one with `Booking`. Fields: `transaction_id` (unique), `amount`, `status` (`PENDING`, `SUCCESS`, `FAILED`), timestamps.

### Deletion policy

- `Parent → Booking`: `CASCADE`.
- `LSAProfile → Booking`: `PROTECT` — an LSA with existing bookings cannot be deleted, preserving historical booking integrity.

### Indexes

`Booking` is indexed on `(lsa, start_time, end_time)` to support the overlap-detection query pattern, and separately on `status`.

## API

### Create a booking

```
POST /api/v1/bookings/
```

```json
{
  "parent": 1,
  "lsa": 1,
  "start_time": "2026-08-15T10:00:00Z",
  "end_time": "2026-08-15T11:00:00Z"
}
```

Returns `201` with the booking in `PENDING_PAYMENT`, or `400` with a validation error if the time range is invalid (`start_time` must be strictly before `end_time`) or the slot conflicts with an existing booking. `status` is a read-only field — clients cannot set it directly, which prevents bypassing the payment workflow.

### Search LSAs

```
GET /api/v1/lsas/search/?skill=Dyslexia%20Support&start_time=2026-08-15T10:30:00Z&end_time=2026-08-15T11:30:00Z
```

Returns active LSAs matching the given skill (case-insensitive) who have no conflicting booking in the requested window. `CANCELLED` and `PAYMENT_FAILED` bookings are excluded from the conflict check, so those slots remain bookable.

### Payment webhook

```
POST /api/payments/webhook/
```

```json
{
  "event": "payment.success",
  "transaction_id": "txn_123",
  "booking_id": 1,
  "amount": "1000.00"
}
```

`event` must be `payment.success` or `payment.failed`; anything else is rejected. On success, the associated `Payment` is created as `SUCCESS` and the booking moves to `CONFIRMED`. On failure, `Payment` is `FAILED` and the booking moves to `PAYMENT_FAILED`.

### Debug: N+1 query comparison

```
GET /api/v1/debug/n-plus-one/
```

Returns the query count for fetching active LSAs and their skills, with and without `prefetch_related("skills")`, for demonstration purposes.

## Booking Conflict Detection

Two time ranges are considered overlapping when:

```
existing.start_time < requested.end_time
AND
existing.end_time > requested.start_time
```

This means adjacent bookings (one ending exactly when the next begins) are allowed, while any actual overlap is rejected. Bookings in `CANCELLED` or `PAYMENT_FAILED` status are excluded from this check, so their time slots are released back for booking.

## Concurrency Handling

`create_booking()` runs inside `transaction.atomic()` and takes a row-level lock on the target LSA with `select_for_update()` before checking for conflicts:

```python
with transaction.atomic():
    locked_lsa = LSAProfile.objects.select_for_update().get(pk=lsa.pk)
    ...
    overlapping_booking = (
        Booking.objects.select_for_update()
        .filter(lsa=lsa, start_time__lt=end_time, end_time__gt=start_time)
        .exclude(status__in=[Booking.Status.CANCELLED, Booking.Status.PAYMENT_FAILED])
        .first()
    )
```

This prevents the application-level race where two concurrent requests could both observe the LSA as available before either booking is committed. The second request blocks on the LSA row lock and re-evaluates availability after the first transaction commits.

The payment webhook applies the same pattern: `process_payment_webhook()` is wrapped in `transaction.atomic()` and locks the `Booking` row with `select_for_update()` before mutating payment or booking state.

## Payment Flow & Idempotency

### Payment Initiation

After the booking is created in PENDING_PAYMENT, create_booking() generates a unique transaction ID and calls external_services.create_payment() to initiate payment with the mock gateway. The payment request is made after the database transaction has completed, so database locks are not held while waiting for the external service.

After the booking is created in PENDING_PAYMENT, create_booking() generates a unique transaction ID and calls external_services.create_payment() to initiate payment with the mock gateway. The payment request is made after the database transaction has completed, so database locks are not held while waiting for the external service.

Gateway timeouts and request failures are converted into PaymentGatewayError and logged. The payment webhook is then responsible for the asynchronous final state transition to CONFIRMED or PAYMENT_FAILED.

The payment webhook is then responsible for the asynchronous final state transition to `CONFIRMED` or `PAYMENT_FAILED`.
`process_payment_webhook()` enforces a small state machine:

- A payment can only be processed for a booking currently in `PENDING_PAYMENT`; any other state raises `PaymentProcessingError`.
- If a `Payment` with the same `transaction_id` already exists for the same booking, the webhook is treated as a duplicate retry and returned as a no-op success (idempotent handling for payment-provider retries).
- If the same `transaction_id` is seen attached to a *different* booking, this is rejected as an error.
- The database-level `unique=True` constraint on `Payment.transaction_id` backs this logic with a hard integrity guarantee.

`external_services.create_payment()` wraps calls to a mock payment gateway (`requests.post`, 5s timeout) and converts `Timeout` / `RequestException` into a domain-specific `PaymentGatewayError`, with logging on both the success and failure paths.

## Query Optimization

`bookings/debug_views.py` demonstrates the N+1 problem when loading LSA skills: iterating `LSAProfile.objects.filter(is_active=True)` and accessing `lsa.skills.all()` per LSA issues one query per LSA, versus a constant number of queries when `.prefetch_related("skills")` is applied. The `LSASearchView` uses `prefetch_related("skills")` in production.

## Testing

The test suite currently has **12 tests**, all passing:

```
Found 12 test(s).
System check identified no issues.
............
Ran 12 tests.

OK
```

Coverage includes:

- **Bookings** (`test_bookings.py`) — successful creation, invalid time range rejection, overlap rejection, adjacent-booking acceptance.
- **Search** (`test_search.py`) — skill filtering, exclusion of inactive LSAs, exclusion of LSAs with a conflicting booking.
- **Payments** (`test_payments.py`) — successful payment confirms the booking, failed payment marks it `PAYMENT_FAILED`, duplicate webhook delivery is idempotent (no duplicate `Payment` row, booking stays `CONFIRMED`).
- **External gateway** (`test_external_services.py`) — successful gateway call and timeout handling, with gateway failures converted into `PaymentGatewayError` (the timeout test intentionally logs a "Payment gateway request timed out" message; that log line is expected, not a failure).
- **Booking/payment integration** (`test_bookings.py`) — verifies that successful booking creation actually initiates payment through the external payment service.

Run the suite with:

```bash
python manage.py test
```

## CI

GitHub Actions (`.github/workflows/tests.yaml`) runs on every push and pull request:

1. Checks out the repository.
2. Sets up Python 3.13.
3. Spins up a `postgres:16` service container.
4. Installs dependencies from `requirements.txt`.
5. Runs `python manage.py migrate`.
6. Runs `python manage.py test`.

## Setup & Local Development

**Requirements:** Python 3.13, PostgreSQL.

```bash
git clone https://github.com/AkshitaChadha/Habot_lsa_booking.git
cd Habot_lsa_booking
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (not committed — see `.gitignore`):

```
DB_NAME=habot_booking
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

Then:

```bash
python manage.py migrate
python manage.py test
python manage.py runserver
```

## Key Engineering Decisions

- **Service layer separation** — `create_booking()` and `process_payment_webhook()` live outside the view layer, keeping business-critical, testable logic independent of HTTP concerns.
- **Server-controlled state** — `Booking.status` is read-only on the create serializer; clients cannot set a booking to `CONFIRMED` directly.
- **`select_for_update()` + `transaction.atomic()`** — the core mechanism protecting both booking creation and payment processing from race conditions.
- **Unique constraints as a second line of defense** — `Parent.email`, `LSAProfile.email`, `Skill.name`, and `Payment.transaction_id` are all unique at the database level, not just validated in application code.
- **`PROTECT` on `Booking.lsa`** — deleting an LSA with existing bookings is blocked, preserving historical records.
- **Idempotent webhook handling** — payment webhooks are safe to retry, checked by `transaction_id` before any state mutation.
- **Custom exceptions** (`BookingConflictError`, `PaymentProcessingError`, `PaymentGatewayError`) — separate expected business failures from unhandled errors.

## Scope & Production Considerations

This implementation is intentionally scoped to the booking and payment workflow required for the assignment. It does **not** currently implement authentication/authorization, integration with a real payment provider (the current gateway is a mock endpoint), webhook signature verification, rate limiting, or pagination. 

### Possible future improvements

- Authentication and role-based access (parent vs. LSA).
- Real payment provider integration with signed/verified webhooks.
- Pagination and filtering on the search endpoint.
- Structured error response format.
- OpenAPI/Swagger documentation.
- Booking cancellation and refund flows.
- Containerized deployment and production secrets management.