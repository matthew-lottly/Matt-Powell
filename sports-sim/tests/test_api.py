"""Tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from sports_sim.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAPI:
    def test_list_sports(self, client):
        res = client.get("/api/sports")
        assert res.status_code == 200
        assert "soccer" in res.json()["sports"]

    def test_create_simulation(self, client):
        res = client.post("/api/simulations", json={"sport": "soccer", "seed": 42, "fidelity": "fast"})
        assert res.status_code == 200
        data = res.json()
        assert "game_id" in data
        assert data["sport"] == "soccer"
        assert data["is_finished"] is False

    def test_run_simulation(self, client):
        create = client.post("/api/simulations", json={"sport": "basketball", "seed": 1, "fidelity": "fast"})
        gid = create.json()["game_id"]
        run = client.post(f"/api/simulations/{gid}/run")
        assert run.status_code == 200
        assert run.json()["is_finished"] is True

    def test_get_simulation(self, client):
        create = client.post("/api/simulations", json={"sport": "baseball", "seed": 7, "fidelity": "fast"})
        gid = create.json()["game_id"]
        client.post(f"/api/simulations/{gid}/run")
        res = client.get(f"/api/simulations/{gid}")
        assert res.status_code == 200
        assert res.json()["is_finished"] is True

    def test_list_simulations(self, client):
        client.post("/api/simulations", json={"sport": "soccer", "seed": 99, "fidelity": "fast"})
        res = client.get("/api/simulations")
        assert res.status_code == 200
        assert len(res.json()["simulations"]) >= 1

    def test_delete_simulation(self, client):
        create = client.post("/api/simulations", json={"sport": "soccer", "seed": 55, "fidelity": "fast"})
        gid = create.json()["game_id"]
        res = client.delete(f"/api/simulations/{gid}")
        assert res.status_code == 200
        assert client.get(f"/api/simulations/{gid}").status_code == 404

    def test_not_found(self, client):
        assert client.get("/api/simulations/nonexistent").status_code == 404
        assert client.post("/api/simulations/nonexistent/run").status_code == 404

    def test_websocket_simulate(self, client):
        with client.websocket_connect("/ws/simulate") as ws:
            ws.send_json({"sport": "soccer", "seed": 42, "fidelity": "fast", "ticks_per_second": 5})
            data = ws.receive_json()
            assert "game_id" in data
            # Read remaining messages until done
            while not data.get("is_finished"):
                data = ws.receive_json()
            assert data["is_finished"] is True
