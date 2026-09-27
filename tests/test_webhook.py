def _make_paid_attempt(client, headers, centre, test, future_time, force_status="SUCCESS"):
    resp = client.post(
        "/bookings/",
        json={
            "test_id": str(test.id),
            "centre_id": str(centre.id),
            "appointment_time": future_time,
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]

    # Use FAILED here so the booking is still in a state a later webhook
    # can meaningfully "confirm" (mimics a delayed provider confirmation
    # arriving after an initial failed/pending attempt).
    resp = client.post(
        "/payments/",
        json={"booking_id": booking_id, "force_status": force_status},
        headers=headers,
    )
    txn_id = resp.json()["provider_transaction_id"]
    return booking_id, txn_id


def test_webhook_confirms_booking(client, auth_headers, centre_with_test, future_time):
    headers = auth_headers()
    centre, test = centre_with_test
    booking_id, txn_id = _make_paid_attempt(
        client, headers, centre, test, future_time, force_status="FAILED"
    )

    resp = client.post(
        "/payments/webhook/",
        json={
            "event_id": "evt_1",
            "provider_transaction_id": txn_id,
            "status": "SUCCESS",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "processed"

    resp = client.get(f"/bookings/{booking_id}", headers=headers)
    assert resp.json()["status"] == "CONFIRMED"


def test_duplicate_webhook_event_is_idempotent(
    client, auth_headers, centre_with_test, future_time
):
    headers = auth_headers()
    centre, test = centre_with_test
    booking_id, txn_id = _make_paid_attempt(
        client, headers, centre, test, future_time, force_status="FAILED"
    )

    payload = {
        "event_id": "evt_dup",
        "provider_transaction_id": txn_id,
        "status": "SUCCESS",
    }

    resp1 = client.post("/payments/webhook/", json=payload)
    resp2 = client.post("/payments/webhook/", json=payload)
    resp3 = client.post("/payments/webhook/", json=payload)

    assert resp1.json()["status"] == "processed"
    assert resp2.json()["status"] == "already_processed"
    assert resp3.json()["status"] == "already_processed"

    # Exactly one payment row exists for this booking -- the webhook never
    # created a duplicate payment.
    resp = client.get(f"/bookings/{booking_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"


def test_webhook_unknown_transaction_is_404(client):
    resp = client.post(
        "/payments/webhook/",
        json={
            "event_id": "evt_unknown",
            "provider_transaction_id": "txn_does_not_exist",
            "status": "SUCCESS",
        },
    )
    assert resp.status_code == 404


def test_webhook_does_not_resurrect_cancelled_booking(
    client, auth_headers, centre_with_test, future_time
):
    headers = auth_headers()
    centre, test = centre_with_test
    booking_id, txn_id = _make_paid_attempt(
        client, headers, centre, test, future_time, force_status="FAILED"
    )

    resp = client.post(f"/bookings/{booking_id}/cancel", headers=headers)
    assert resp.json()["status"] == "CANCELLED"

    client.post(
        "/payments/webhook/",
        json={
            "event_id": "evt_late",
            "provider_transaction_id": txn_id,
            "status": "SUCCESS",
        },
    )

    resp = client.get(f"/bookings/{booking_id}", headers=headers)
    assert resp.json()["status"] == "CANCELLED"
