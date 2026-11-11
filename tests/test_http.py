from fastapi.testclient import TestClient

from incident_lab import runner, server


def test_health_and_invalid_request_do_not_invoke_model(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Model must not run")

    monkeypatch.setattr(server, "invoke", unexpected)
    c = TestClient(server.app)
    assert c.get("/ping").json() == {"status": "Healthy"}
    assert c.post("/invocations", json={"incident_id": "oops"}).status_code == 422
    assert c.post("/invocations", json={"incident_id": "INC-001", "tenant": "atelier-b"}).status_code == 422


def test_http_invocation_has_new_request_and_fixed_tenant(monkeypatch):
    calls = []

    def fake(incident, mode, tenant):
        calls.append((incident, mode, tenant))
        return {"ok": True, "report": {"incident_id": incident}}

    monkeypatch.setattr(server, "invoke", fake)
    c = TestClient(server.app)
    for incident in ["INC-001", "INC-002"]:
        assert c.post("/invocations", json={"incident_id": incident}).status_code == 200
    assert calls == [("INC-001", "single", "atelier-a"), ("INC-002", "single", "atelier-a")]


def test_timeout_terminates_worker(monkeypatch):
    import subprocess

    def expired(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(runner.subprocess, "run", expired)
    assert runner.invoke("INC-001", timeout=1)["error"] == "TIMEOUT"
