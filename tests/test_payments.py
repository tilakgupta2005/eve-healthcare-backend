def _make_booking(client, headers, centre, test, future_time):
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
    return resp.json()["id"]


def test_forced_success_payment_confirms_booking(
    client, auth_headers, centre_with_test, future_time
):
    headers = auth_headers()
    centre, test = centre_with_test
    booking_id = _make_booking(client, headers, centre, test, future_time)

    resp = client.post(
        "/payments/",
        json={"booking_id": booking_id, "force_status": "SUCCESS"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "SUCCESS"

    resp = client.get(f"/bookings/{booking_id}", headers=headers)
    assert resp.json()["status"] == "CONFIRMED"


def test_forced_failed_payment_marks_booking_failed(
    client, auth_headers, centre_with_test, future_time
):
    headers = auth_headers()
    centre, test = centre_with_test
    booking_id = _make_booking(client, headers, centre, test, future_time)

    resp = client.post(
        "/payments/",
        json={"booking_id": booking_id, "force_status": "FAILED"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "FAILED"

    resp = client.get(f"/bookings/{booking_id}", headers=headers)
    assert resp.json()["status"] == "FAILED"


def test_cannot_pay_twice_for_confirmed_booking(
    client, auth_headers, centre_with_test, future_time
):
    headers = auth_headers()
    centre, test = centre_with_test
    booking_id = _make_booking(client, headers, centre, test, future_time)

    client.post(
        "/payments/", json={"booking_id": booking_id, "force_status": "SUCCESS"}, headers=headers
    )
    resp = client.post(
        "/payments/", json={"booking_id": booking_id, "force_status": "SUCCESS"}, headers=headers
    )
    assert resp.status_code == 400


def test_cannot_pay_for_someone_elses_booking(
    client, auth_headers, centre_with_test, future_time
):
    owner_headers = auth_headers(email="owner2@example.com")
    centre, test = centre_with_test
    booking_id = _make_booking(client, owner_headers, centre, test, future_time)

    other_headers = auth_headers(email="other2@example.com")
    resp = client.post(
        "/payments/",
        json={"booking_id": booking_id, "force_status": "SUCCESS"},
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_payment_for_unknown_booking_is_404(client, auth_headers):
    headers = auth_headers()
    resp = client.post(
        "/payments/",
        json={
            "booking_id": "00000000-0000-0000-0000-000000000000",
            "force_status": "SUCCESS",
        },
        headers=headers,
    )
    assert resp.status_code == 404
