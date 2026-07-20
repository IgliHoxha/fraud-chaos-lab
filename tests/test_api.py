from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz_defaults_to_dry_run():
    resp = client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["dry_run"] is True  # no target configured by default


def test_metrics_exposed():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "chaos_requests_total" in resp.text or resp.text == ""


def test_subscription_churn_dry_run_small():
    resp = client.post("/chaos/subscription-churn", json={"count": 25, "concurrency": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["scenario"] == "subscription-churn"
    assert body["dry_run"] is True
    assert body["requested"] == 25
    assert body["succeeded"] == 25
    assert body["failed"] == 0


def test_service_1_flood_dry_run():
    resp = client.post("/chaos/service-1-flood", json={"count": 10})
    assert resp.status_code == 200
    assert resp.json()["scenario"] == "service-1-flood"


def test_service_2_storm_dry_run():
    resp = client.post("/chaos/service-2-storm", json={"count": 10})
    assert resp.status_code == 200
    assert resp.json()["scenario"] == "service-2-storm"


def test_count_is_clamped_to_max():
    # Default max_storm_size is 20000; asking for more must be clamped.
    resp = client.post("/chaos/service-1-flood", json={"count": 999999, "concurrency": 200})
    assert resp.status_code == 200
    assert resp.json()["requested"] == 20000
