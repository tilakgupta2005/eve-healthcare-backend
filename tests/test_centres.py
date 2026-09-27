def test_non_admin_cannot_create_centre(client, auth_headers):
    headers = auth_headers()
    resp = client.post(
        "/centres/", json={"name": "X Labs", "location": "Pune"}, headers=headers
    )
    assert resp.status_code == 403


def test_admin_can_create_centre_and_add_test(client, auth_headers):
    headers = auth_headers(email="admin@example.com", is_admin=True)

    resp = client.post(
        "/centres/", json={"name": "X Labs", "location": "Pune"}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    centre_id = resp.json()["id"]

    resp = client.post(
        f"/centres/{centre_id}/tests",
        json={"name": "Lipid Profile", "price": "699.00"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["centre_id"] == centre_id


def test_list_and_get_centre_is_public(client, centre_with_test):
    centre, _ = centre_with_test
    resp = client.get("/centres/")
    assert resp.status_code == 200
    assert any(c["id"] == str(centre.id) for c in resp.json())

    resp = client.get(f"/centres/{centre.id}")
    assert resp.status_code == 200


def test_get_unknown_centre_is_404(client):
    resp = client.get("/centres/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_get_centre_bad_uuid_is_400_not_500(client):
    resp = client.get("/centres/not-a-uuid")
    assert resp.status_code == 422  # FastAPI's own path-param validation
