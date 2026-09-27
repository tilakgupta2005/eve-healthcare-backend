def test_create_booking_success(client, auth_headers, centre_with_test, future_time):
    headers = auth_headers()
    centre, test = centre_with_test

    resp = client.post(
        "/bookings/",
        json={
            "test_id": str(test.id),
            "centre_id": str(centre.id),
            "appointment_time": future_time,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "PENDING"
    assert float(body["amount"]) == 499.00


def test_create_booking_unknown_centre_is_404(client, auth_headers, centre_with_test, future_time):
    headers = auth_headers()
    _, test = centre_with_test

    resp = client.post(
        "/bookings/",
        json={
            "test_id": str(test.id),
            "centre_id": "00000000-0000-0000-0000-000000000000",
            "appointment_time": future_time,
        },
        headers=headers,
    )
    assert resp.status_code == 404


def test_create_booking_test_not_at_centre_is_400(client, auth_headers, db, future_time):
    from app.models.centre import DiagnosticCentre
    from app.models.test import DiagnosticTest

    centre_a = DiagnosticCentre(name="A", location="Delhi")
    centre_b = DiagnosticCentre(name="B", location="Mumbai")
    db.add_all([centre_a, centre_b])
    db.commit()
    test_at_b = DiagnosticTest(centre_id=centre_b.id, name="X-Ray", price=300)
    db.add(test_at_b)
    db.commit()
    db.refresh(test_at_b)

    headers = auth_headers()
    resp = client.post(
        "/bookings/",
        json={
            "test_id": str(test_at_b.id),
            "centre_id": str(centre_a.id),
            "appointment_time": future_time,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_create_booking_past_appointment_rejected(client, auth_headers, centre_with_test):
    headers = auth_headers()
    centre, test = centre_with_test
    resp = client.post(
        "/bookings/",
        json={
            "test_id": str(test.id),
            "centre_id": str(centre.id),
            "appointment_time": "2020-01-01T10:00:00Z",
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_user_cannot_view_others_booking(client, auth_headers, centre_with_test, future_time):
    owner_headers = auth_headers(email="owner@example.com")
    centre, test = centre_with_test
    resp = client.post(
        "/bookings/",
        json={
            "test_id": str(test.id),
            "centre_id": str(centre.id),
            "appointment_time": future_time,
        },
        headers=owner_headers,
    )
    booking_id = resp.json()["id"]

    other_headers = auth_headers(email="other@example.com")
    resp = client.get(f"/bookings/{booking_id}", headers=other_headers)
    assert resp.status_code == 403


def test_cancel_booking_then_cancel_again_is_idempotent(
    client, auth_headers, centre_with_test, future_time
):
    headers = auth_headers()
    centre, test = centre_with_test
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

    resp = client.post(f"/bookings/{booking_id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"

    # Cancelling an already-cancelled booking is a harmless no-op, not an error.
    resp = client.post(f"/bookings/{booking_id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"
