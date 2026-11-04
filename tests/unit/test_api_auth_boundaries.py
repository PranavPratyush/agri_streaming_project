"""Unit tests for AgriKafka-Agent API authentication, roles, and security boundaries.

Proves:
1. Field ownership isolation: Farmers cannot view or modify parcels they do not own.
2. Role hierarchy: Agronomists and Admins have authorized system-wide visibility.
3. Operations endpoints restricted from unprivileged roles.
4. Admin debug state endpoint requires strict API key validation.
5. Invariant enforcement: Rejection of invalid human decision states and actions.
6. Zero physical actuation invariant: Actions update advisory workflow only.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agri_api.main import app
from agri_api.dependencies import LocalMemoryRepository


@pytest.fixture(autouse=True)
def reset_local_repository():
    from agri_api import dependencies
    dependencies._REPO_INSTANCE = LocalMemoryRepository()
    yield
    dependencies._REPO_INSTANCE = None


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestFieldOwnershipBoundaries:
    """Verifies that farmers are strictly isolated to their own field parcels."""

    def test_farmer_cannot_access_unowned_field(self, client: TestClient):
        # Farmer belongs to 'field-kolar-001', attempting to access 'field-demo-parcel'
        headers = {
            "X-User-Role": "farmer",
            "X-User-ID": "farmer-kolar",
            "X-Farmer-ID": "field-kolar-001",
        }
        res = client.get("/api/v1/fields/field-demo-parcel", headers=headers)
        assert res.status_code == 403
        data = res.json()
        assert "access denied" in data["message"].lower()

    def test_farmer_cannot_update_unowned_field(self, client: TestClient):
        headers = {
            "X-User-Role": "farmer",
            "X-User-ID": "farmer-kolar",
            "X-Farmer-ID": "field-kolar-001",
        }
        payload = {"current_growth_stage": "harvesting"}
        res = client.patch("/api/v1/fields/field-demo-parcel", json=payload, headers=headers)
        assert res.status_code == 403

    def test_farmer_can_access_own_field(self, client: TestClient):
        headers = {
            "X-User-Role": "farmer",
            "X-User-ID": "farmer-kolar",
            "X-Farmer-ID": "field-kolar-001",
        }
        res = client.get("/api/v1/fields/field-kolar-001", headers=headers)
        assert res.status_code == 200
        assert res.json()["field_id"] == "field-kolar-001"

    def test_agronomist_can_access_any_field(self, client: TestClient):
        headers = {
            "X-User-Role": "agronomist",
            "X-User-ID": "agronomist-kolar",
        }
        res1 = client.get("/api/v1/fields/field-kolar-001", headers=headers)
        res2 = client.get("/api/v1/fields/field-demo-parcel", headers=headers)
        assert res1.status_code == 200
        assert res2.status_code == 200


class TestPrivilegedOperationsSecurity:
    """Verifies access control for operational diagnostics and administrative endpoints."""

    def test_farmer_cannot_access_operations_status(self, client: TestClient):
        headers = {
            "X-User-Role": "farmer",
            "X-User-ID": "farmer-kolar",
            "X-Farmer-ID": "field-kolar-001",
        }
        res = client.get("/api/v1/operations/status", headers=headers)
        assert res.status_code == 403
        data = res.json()
        assert "agronomist or admin role" in data["message"].lower()

    def test_agronomist_can_access_operations_status(self, client: TestClient):
        headers = {
            "X-User-Role": "agronomist",
            "X-User-ID": "agronomist-01",
        }
        res = client.get("/api/v1/operations/status", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "OPERATIONAL"

    def test_admin_debug_route_requires_api_key(self, client: TestClient):
        headers = {
            "X-User-Role": "admin",
            "X-User-ID": "admin-01",
            "X-API-Key": "wrong-key",
        }
        res = client.get("/api/v1/admin/debug/state", headers=headers)
        assert res.status_code == 403

    def test_admin_debug_route_succeeds_with_valid_key(self, client: TestClient):
        headers = {
            "X-User-Role": "admin",
            "X-User-ID": "admin-01",
            "X-API-Key": "agri-admin-secret-key",
        }
        res = client.get("/api/v1/admin/debug/state", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "python_version" in data
        assert "registered_fields_count" in data


class TestHumanDecisionInvariants:
    """Verifies safety guards around advisory actions and supervisor state machine."""

    def test_decision_on_non_existent_investigation_returns_404(self, client: TestClient):
        headers = {
            "X-User-Role": "agronomist",
            "X-User-ID": "agronomist-01",
        }
        payload = {
            "action": "APPROVE",
            "reviewer_id": "agronomist-01",
            "comments": "Test notes",
        }
        res = client.post("/api/v1/investigations/non-existent-run-id/human-decision", json=payload, headers=headers)
        assert res.status_code == 404

    def test_invalid_decision_type_rejected(self, client: TestClient):
        headers = {
            "X-User-Role": "agronomist",
            "X-User-ID": "agronomist-01",
        }
        payload = {
            "action": "ACTUATE_PUMP_HARDWARE",  # Strictly disallowed
            "reviewer_id": "agronomist-01",
            "comments": "Invalid command",
        }
        # First create an investigation to ensure 400 is returned by validator
        inv_res = client.post(
            "/api/v1/investigations",
            json={"field_id": "field-kolar-001", "alert_id": "c1a4169f-48bd-494d-a2e0-32c3f2e9688a"},
            headers=headers,
        )
        assert inv_res.status_code == 201
        run_id = inv_res.json()["run_id"]

        res = client.post(f"/api/v1/investigations/{run_id}/human-decision", json=payload, headers=headers)
        assert res.status_code in (400, 422)

    def test_farmer_cannot_approve_advisory_without_agronomist_role(self, client: TestClient):
        headers = {
            "X-User-Role": "farmer",
            "X-User-ID": "farmer-kolar",
            "X-Farmer-ID": "field-kolar-001",
        }
        payload = {"action": "APPROVE"}
        res = client.post("/api/v1/advisories/rec-12345/action", json=payload, headers=headers)
        assert res.status_code == 403
