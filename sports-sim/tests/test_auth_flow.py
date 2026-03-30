import os
from fastapi.testclient import TestClient


def test_token_and_protected_endpoints(monkeypatch):
    # Enable auth and set a known secret
    monkeypatch.setenv("SPORTS_SIM_AUTH_ENABLED", "1")
    monkeypatch.setenv("SPORTS_SIM_AUTH_SECRET", "test-secret")

    # import app after env configured
    from sports_sim.api.app import app

    client = TestClient(app)

    # Request token with known user
    res = client.post("/api/auth/token", json={"username": "admin", "password": "adminpass"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    # Create simulation (protected)
    create = client.post("/api/simulations", json={"sport": "soccer", "seed": 1, "fidelity": "fast"}, headers=headers)
    assert create.status_code == 200
    gid = create.json()["game_id"]

    # Run simulation
    run = client.post(f"/api/simulations/{gid}/run", headers=headers)
    assert run.status_code == 200

    # Delete simulation
    delr = client.delete(f"/api/simulations/{gid}", headers=headers)
    assert delr.status_code == 200

    # Non-admin cannot delete: issue token for regular user
    user_res = client.post("/api/auth/token", json={"username": "user", "password": "userpass"})
    assert user_res.status_code == 200
    user_token = user_res.json()["access_token"]
    uh = {"Authorization": f"Bearer {user_token}"}
    # create another sim
    create2 = client.post("/api/simulations", json={"sport": "soccer", "seed": 2, "fidelity": "fast"}, headers=headers)
    gid2 = create2.json()["game_id"]
    # attempt delete with non-admin
    delr2 = client.delete(f"/api/simulations/{gid2}", headers=uh)
    assert delr2.status_code == 403
