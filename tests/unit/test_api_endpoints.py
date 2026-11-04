"""Unit tests for AgriKafka-Agent Backend API endpoints.

Covers:
- Operations (/healthz, /readyz, /metrics, /api/v1/operations/status)
- Field management (/api/v1/fields)
- Telemetry & Sensor Health (/api/v1/fields/{id}/observations, trends, freshness)
- Candidate Alerts & Evidence (/api/v1/alerts)
- Supervisor-mediated Multi-Agent Investigations (/api/v1/investigations)
- Human Decision & Advisory Approval (/api/v1/investigations/{id}/human-decision, /api/v1/advisories)
- Farmer Feedback & System Auditing (/api/v1/feedback)
"""

from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from agri_api.main import app
from agri_api.dependencies import LocalMemoryRepository


@pytest.fixture(autouse=True)
def reset_local_repository():
    """Ensure clean repository state before each test."""
    from agri_api import dependencies
    dependencies._REPO_INSTANCE = LocalMemoryRepository()
    yield
    dependencies._REPO_INSTANCE = None


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def agronomist_headers() -> dict[str, str]:
    return {
        "X-User-Role": "agronomist",
        "X-User-ID": "agronomist-01",
    }


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {
        "X-User-Role": "admin",
        "X-User-ID": "admin-01",
        "X-API-Key": "agri-admin-secret-key",
    }


@pytest.fixture
def farmer_headers() -> dict[str, str]:
    return {
        "X-User-Role": "farmer",
        "X-User-ID": "farmer-kolar",
        "X-Farmer-ID": "field-kolar-001",
    }


class TestOperationsEndpoints:
    """Verifies service health, liveness, readiness, and metrics endpoints."""

    def test_healthz_liveness_probe(self, client: TestClient):
        res = client.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "agri-api"
        assert data["status"] == "HEALTHY"
        assert "api_server" in data["components"]
        assert data["components"]["api_server"]["status"] == "UP"

    def test_readyz_readiness_probe(self, client: TestClient):
        res = client.get("/readyz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert "database" in data["components"]

    def test_prometheus_metrics_scrape(self, client: TestClient):
        res = client.get("/metrics")
        assert res.status_code == 200
        assert "agri_" in res.text or "# HELP" in res.text or "# TYPE" in res.text

    def test_operations_status_privileged(self, client: TestClient, agronomist_headers: dict[str, str]):
        res = client.get("/api/v1/operations/status", headers=agronomist_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "OPERATIONAL"
        assert "timescaledb_status" in data


class TestFieldsEndpoints:
    """Verifies field profile retrieval, status, and update endpoints."""

    def test_list_fields_returns_parcels(self, client: TestClient, agronomist_headers: dict[str, str]):
        res = client.get("/api/v1/fields", headers=agronomist_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 2
        field_ids = [f["field_id"] for f in data["items"]]
        assert "field-kolar-001" in field_ids

    def test_get_field_by_id_success(self, client: TestClient, farmer_headers: dict[str, str]):
        res = client.get("/api/v1/fields/field-kolar-001", headers=farmer_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["field_id"] == "field-kolar-001"
        assert data["crop_name"] == "finger_millet"
        assert data["current_growth_stage"] == "flowering"

    def test_get_field_not_found(self, client: TestClient, agronomist_headers: dict[str, str]):
        res = client.get("/api/v1/fields/non-existent-field-999", headers=agronomist_headers)
        assert res.status_code == 404

    def test_update_field_growth_stage(self, client: TestClient, agronomist_headers: dict[str, str]):
        update_payload = {"current_growth_stage": "grain_filling"}
        res = client.put("/api/v1/fields/field-kolar-001", json=update_payload, headers=agronomist_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["action"] == "UPDATE_FIELD"

        # Verify updated value
        get_res = client.get("/api/v1/fields/field-kolar-001", headers=agronomist_headers)
        assert get_res.status_code == 200
        assert get_res.json()["current_growth_stage"] == "grain_filling"

    def test_get_field_status(self, client: TestClient, farmer_headers: dict[str, str]):
        res = client.get("/api/v1/fields/field-kolar-001/status", headers=farmer_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["field_id"] == "field-kolar-001"
        assert data["sensor_health_overall"] == "HEALTHY"
        assert "latest_soil_moisture" in data


class TestTelemetryEndpoints:
    """Verifies observation history, temporal trends, and sensor freshness."""

    def test_get_field_observations(self, client: TestClient, farmer_headers: dict[str, str]):
        res = client.get("/api/v1/fields/field-kolar-001/observations", headers=farmer_headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert len(data["items"]) > 0
        assert data["items"][0]["sensor_id"] is not None

    def test_get_field_trends(self, client: TestClient, farmer_headers: dict[str, str]):
        res = client.get("/api/v1/fields/field-kolar-001/trends", headers=farmer_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["field_id"] == "field-kolar-001"
        assert "soil_moisture_trend" in data

    def test_get_sensors_freshness(self, client: TestClient, agronomist_headers: dict[str, str]):
        res = client.get("/api/v1/sensors/freshness", headers=agronomist_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        assert data[0]["health_state"] == "HEALTHY"


class TestAlertsAndInvestigations:
    """Verifies candidate alerts, Supervisor-mediated investigations, and timeline."""

    def test_list_candidate_alerts(self, client: TestClient, farmer_headers: dict[str, str]):
        res = client.get("/api/v1/alerts?field_id=field-kolar-001", headers=farmer_headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        assert data["items"][0]["alert_type"] == "SOIL_MOISTURE_DEPLETION"

    def test_trigger_supervisor_investigation(self, client: TestClient, agronomist_headers: dict[str, str]):
        payload = {
            "candidate_alert": {
                "alert_id": str(uuid.uuid4()),
                "field_id": "field-kolar-001",
                "crop_variety": "Finger Millet (Ragi GPU-28)",
                "growth_stage": "Flowering / Grain Filling",
                "risk_type": "SOIL_MOISTURE_DEPLETION",
                "severity": "HIGH",
                "composite_stress_index": 0.76,
                "sensor_health_state": "HEALTHY",
                "observations": [
                    {"sensor_id": "soil-01", "variable": "soil_moisture", "numeric_value": 0.11, "unit": "m3/m3"}
                ],
                "sensor_health_results": [
                    {"sensor_id": "soil-01", "health_state": "HEALTHY", "reason_code": "ALL_SENSORS_VALID"}
                ],
            },
            "priority": "HIGH",
            "notes": "Triggered automated field verification test",
        }
        res = client.post("/api/v1/investigations", json=payload, headers=agronomist_headers)
        assert res.status_code == 201
        run_data = res.json()
        run_id = run_data["run_id"]
        assert run_data["field_id"] == "field-kolar-001"
        assert run_data["current_state"] in ("awaiting_human_review", "AWAITING_HUMAN_REVIEW", "COMPLETED", "ABSTAINED")
        assert run_data["reliability_assessment"] is not None

        # Check Timeline
        timeline_res = client.get(f"/api/v1/investigations/{run_id}/timeline", headers=agronomist_headers)
        assert timeline_res.status_code == 200
        timeline = timeline_res.json()
        assert len(timeline) >= 4

        # Check Agent Messages / Handoffs
        messages_res = client.get(f"/api/v1/investigations/{run_id}/messages", headers=agronomist_headers)
        assert messages_res.status_code == 200
        messages = messages_res.json()
        assert len(messages) >= 4
        # Verify no raw prompt or private secrets leak in message previews
        for msg in messages:
            assert "prompt" not in msg["concise_summary"].lower()

        # Check Citations
        citations_res = client.get(f"/api/v1/investigations/{run_id}/citations", headers=agronomist_headers)
        assert citations_res.status_code == 200
        citations = citations_res.json()
        assert isinstance(citations, list)

        # Submit Human Decision (APPROVE)
        decision_payload = {
            "action": "APPROVE",
            "comments": "Confirmed dry spell against field inspection report",
            "idempotency_key": f"test-idem-{run_id}",
        }
        decision_res = client.post(f"/api/v1/investigations/{run_id}/human-decision", json=decision_payload, headers=agronomist_headers)
        assert decision_res.status_code == 200
        decision_data = decision_res.json()
        assert decision_data["action_taken"] == "APPROVE"
        assert decision_data["resulting_status"] == "approved_by_human"


class TestAdvisoriesAndFarmerFeedback:
    """Verifies advisory proposals, human decision actions, and farmer feedback."""

    def test_list_and_act_on_advisory(self, client: TestClient, agronomist_headers: dict[str, str]):
        # Setup an advisory proposal in repo
        from agri_api.dependencies import get_repository
        repo = get_repository()
        rec_id = "rec-" + str(uuid.uuid4())[:8]
        repo.create_farmer_recommendation({
            "recommendation_id": rec_id,
            "field_id": "field-kolar-001",
            "crop_name": "finger_millet",
            "growth_stage": "flowering",
            "action_title": "Protective Irrigation Advisory",
            "action_body": "Apply 25mm protective irrigation due to soil moisture depletion.",
            "urgency": "HIGH",
            "approval_status": "PROPOSED",
            "cited_evidence_ids": ["CIT-FAO56-001"],
            "created_at": "2026-11-04T12:00:00Z",
        })

        # List advisories
        list_res = client.get("/api/v1/advisories?field_id=field-kolar-001", headers=agronomist_headers)
        assert list_res.status_code == 200
        advisories = list_res.json()["items"]
        assert any(a["recommendation_id"] == rec_id for a in advisories)

        # Approve advisory
        act_res = client.post(
            f"/api/v1/advisories/{rec_id}/action",
            json={"action": "APPROVE", "comments": "Approved for SMS broadcast"},
            headers=agronomist_headers,
        )
        assert act_res.status_code == 200
        assert act_res.json()["action_taken"] == "APPROVE"

    def test_record_farmer_feedback(self, client: TestClient, farmer_headers: dict[str, str]):
        feedback_payload = {
            "recommendation_id": "rec-demo-01",
            "field_id": "field-kolar-001",
            "rating": 5,
            "action_taken": True,
            "observed_outcome": "Soil moisture stabilized after 25mm irrigation",
            "feedback_comments": "Irrigated field using borewell water as advised",
        }
        post_res = client.post("/api/v1/feedback", json=feedback_payload, headers=farmer_headers)
        assert post_res.status_code == 201
        data = post_res.json()
        assert data["field_id"] == "field-kolar-001"
        assert data["status"] == "RECORDED"

        # List feedback
        get_res = client.get("/api/v1/feedback?field_id=field-kolar-001", headers=farmer_headers)
        assert get_res.status_code == 200
        body = get_res.json()
        assert "items" in body
        assert len(body["items"]) >= 1
