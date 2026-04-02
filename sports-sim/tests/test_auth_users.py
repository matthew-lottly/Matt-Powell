from fastapi.testclient import TestClient


def test_admin_can_list_and_create_users(monkeypatch):
    # Enable auth and set secret
    monkeypatch.setenv("SPORTS_SIM_AUTH_ENABLED", "1")
    monkeypatch.setenv("SPORTS_SIM_AUTH_SECRET", "test-secret")

    from sports_sim.api.app import app

    client = TestClient(app)

    # get token for admin
    r = client.post("/api/auth/token", json={"username": "admin", "password": "adminpass"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # list users
    list_res = client.get("/api/auth/users", headers=headers)
    assert list_res.status_code == 200
    assert "admin" in list_res.json()

    # create a new user
    create_res = client.post(
        "/api/auth/users",
        json={"username": "newuser", "password": "p", "role": "user"},
        headers=headers,
    )
    assert create_res.status_code == 200
    assert create_res.json()["username"] == "newuser"

    # non-admin cannot list users
    user_token = client.post(
        "/api/auth/token",
        json={"username": "user", "password": "userpass"},
    ).json()["access_token"]
    uh = {"Authorization": f"Bearer {user_token}"}
    r2 = client.get("/api/auth/users", headers=uh)
    assert r2.status_code == 403
