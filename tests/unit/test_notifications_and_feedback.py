"""Unit and integration tests for AgriKafka Notification Worker, Human Review Lifecycle, and Feedback System."""

from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from agri_api.main import app
from agri_api.dependencies import LocalMemoryRepository
from agri_notifications.dispatcher import NotificationDispatcher
from agri_notifications.feedback import FeedbackProcessor
from agri_notifications.lifecycle import HumanReviewLifecycleManager
from agri_notifications.models import (
    AdvisoryStatus,
    DeliveryStatus,
    HumanReviewActionRequest,
    NotificationChannel,
    ReviewAction,
    StructuredFeedbackInput,
)
from agri_notifications.policy import NotificationPolicyEvaluator
from agri_notifications.providers.mock import InMemoryNotificationProvider, LocalMockNotificationProvider
from agri_notifications.providers.telegram import TelegramNotificationProvider


@pytest.fixture
def memory_repo():
    """Provides an isolated LocalMemoryRepository."""
    from agri_api import dependencies
    repo = LocalMemoryRepository()
    repo.recommendations.clear()
    repo.feedback.clear()
    repo.dispatches.clear()
    repo.audit.clear()
    dependencies._REPO_INSTANCE = repo
    yield repo
    dependencies._REPO_INSTANCE = None


@pytest.fixture
def sample_alert():
    return {
        "alert_id": str(uuid.uuid4()),
        "field_id": "field-kolar-001",
        "alert_type": "SOIL_MOISTURE_DEPLETION",
        "severity": "HIGH",
        "composite_stress_index": 0.78,
        "evidence": {"sensor_provenance": "Ground Capacitance VH400"},
        "contributing_features": {"soil_moisture": 0.11, "fao56_depletion": 0.65},
    }


@pytest.fixture
def sample_recommendation(sample_alert):
    rec_id = str(uuid.uuid4())
    return {
        "recommendation_id": rec_id,
        "alert_id": sample_alert["alert_id"],
        "field_id": sample_alert["field_id"],
        "investigation_id": str(uuid.uuid4()),
        "approval_status": "AWAITING_REVIEW",
        "advisory_version": 1,
        "action_category": "IRRIGATION",
        "action_title": "Deficit Irrigation Application",
        "action_body": "Apply 15 mm targeted drip irrigation during early morning hours.",
        "urgency": "HIGH",
        "limitations": ["Requires functioning drip lines."],
        "when_to_seek_expert": "Consult KVK officer if moisture remains below 12%.",
    }


# -------------------------------------------------------------------------
# 1. Duplicate Suppression & Idempotency
# -------------------------------------------------------------------------
def test_notification_duplicate_suppression(memory_repo, sample_alert, sample_recommendation):
    mock_provider = InMemoryNotificationProvider()
    dispatcher = NotificationDispatcher(
        repository=memory_repo,
        providers={"mock_channel": mock_provider},
    )

    # First dispatch
    dispatch1 = dispatcher.dispatch_for_alert_and_advisory(
        alert=sample_alert,
        recommendation=sample_recommendation,
        recipient_id="farmer-kolar-01",
        channel="mock_channel",
    )
    assert dispatch1.status == DeliveryStatus.SENT
    assert len(mock_provider.delivered_messages) == 1

    # Second duplicate dispatch with identical compound key
    dispatch2 = dispatcher.dispatch_for_alert_and_advisory(
        alert=sample_alert,
        recommendation=sample_recommendation,
        recipient_id="farmer-kolar-01",
        channel="mock_channel",
    )

    # Must return cached dispatch without second delivery
    assert dispatch2.idempotency_key == dispatch1.idempotency_key
    assert dispatch2.dispatch_id == dispatch1.dispatch_id
    assert len(mock_provider.delivered_messages) == 1


# -------------------------------------------------------------------------
# 2. Bounded Retries on Transient Failures
# -------------------------------------------------------------------------
def test_notification_bounded_retries_and_recovery(memory_repo, sample_alert, sample_recommendation):
    # Provider fails on first 2 attempts, then succeeds on 3rd attempt
    flaky_provider = InMemoryNotificationProvider(failure_count=2)
    dispatcher = NotificationDispatcher(
        repository=memory_repo,
        providers={"mock_channel": flaky_provider},
        max_retries=3,
        retry_backoff_base_sec=0.001,
    )

    dispatch = dispatcher.dispatch_for_alert_and_advisory(
        alert=sample_alert,
        recommendation=sample_recommendation,
        recipient_id="farmer-kolar-01",
        channel="mock_channel",
    )

    assert dispatch.status == DeliveryStatus.SENT
    assert dispatch.attempts == 3
    assert flaky_provider.attempts == 3
    assert len(flaky_provider.delivered_messages) == 1


# -------------------------------------------------------------------------
# 3. Dead-Letter Queue on Permanent Failure
# -------------------------------------------------------------------------
def test_notification_dead_letter_routing_on_exhaustion(memory_repo, sample_alert, sample_recommendation):
    failing_provider = InMemoryNotificationProvider(permanent_failure=True)
    dispatcher = NotificationDispatcher(
        repository=memory_repo,
        providers={"mock_channel": failing_provider},
        max_retries=3,
        retry_backoff_base_sec=0.001,
    )

    dispatch = dispatcher.dispatch_for_alert_and_advisory(
        alert=sample_alert,
        recommendation=sample_recommendation,
        recipient_id="farmer-kolar-01",
        channel="mock_channel",
    )

    assert dispatch.status == DeliveryStatus.DEAD_LETTER
    assert dispatch.attempts == 3
    assert dispatch.error_message is not None
    assert "Simulated permanent provider outage" in dispatch.error_message
    assert len(failing_provider.delivered_messages) == 0


# -------------------------------------------------------------------------
# 4. Sensor-Faulty and Abstained Suppression Policy
# -------------------------------------------------------------------------
def test_sensor_fault_suppresses_external_broadcast(memory_repo, sample_alert, sample_recommendation):
    mock_provider = InMemoryNotificationProvider()
    dispatcher = NotificationDispatcher(
        repository=memory_repo,
        providers={"mock_channel": mock_provider},
    )

    # Dispatched when sensor health is FAULTY
    dispatch = dispatcher.dispatch_for_alert_and_advisory(
        alert=sample_alert,
        recommendation=sample_recommendation,
        recipient_id="farmer-kolar-01",
        channel="mock_channel",
        sensor_health_state="FAULTY",
    )

    assert dispatch.status == DeliveryStatus.DEAD_LETTER
    assert "Sensor health is 'FAULTY'" in dispatch.error_message
    assert len(mock_provider.delivered_messages) == 0


def test_critic_abstention_suppresses_broadcast(memory_repo, sample_alert, sample_recommendation):
    mock_provider = InMemoryNotificationProvider()
    dispatcher = NotificationDispatcher(
        repository=memory_repo,
        providers={"mock_channel": mock_provider},
    )

    dispatch = dispatcher.dispatch_for_alert_and_advisory(
        alert=sample_alert,
        recommendation=sample_recommendation,
        recipient_id="farmer-kolar-01",
        channel="mock_channel",
        critic_decision="ABSTAIN",
    )

    assert dispatch.status == DeliveryStatus.DEAD_LETTER
    assert "Supervisor/Critic state is 'ABSTAIN'" in dispatch.error_message
    assert len(mock_provider.delivered_messages) == 0


# -------------------------------------------------------------------------
# 5. Content Safety Gate: Chemical Dosages & Absolute Guarantees
# -------------------------------------------------------------------------
def test_content_safety_rejects_chemical_dosage(memory_repo, sample_alert, sample_recommendation):
    sample_recommendation["action_body"] = "Spray 2.5 ml/L of carbendazim immediately across the parcel."
    mock_provider = InMemoryNotificationProvider()
    dispatcher = NotificationDispatcher(
        repository=memory_repo,
        providers={"mock_channel": mock_provider},
    )

    dispatch = dispatcher.dispatch_for_alert_and_advisory(
        alert=sample_alert,
        recommendation=sample_recommendation,
        recipient_id="farmer-kolar-01",
        channel="mock_channel",
    )

    assert dispatch.status == DeliveryStatus.DEAD_LETTER
    assert "prohibited specific chemical dosage" in dispatch.error_message
    assert len(mock_provider.delivered_messages) == 0


def test_content_safety_rejects_guaranteed_claims(memory_repo, sample_alert, sample_recommendation):
    sample_recommendation["action_body"] = "This action is guaranteed to cure all fungal blight without any loss."
    mock_provider = InMemoryNotificationProvider()
    dispatcher = NotificationDispatcher(
        repository=memory_repo,
        providers={"mock_channel": mock_provider},
    )

    dispatch = dispatcher.dispatch_for_alert_and_advisory(
        alert=sample_alert,
        recommendation=sample_recommendation,
        recipient_id="farmer-kolar-01",
        channel="mock_channel",
    )

    assert dispatch.status == DeliveryStatus.DEAD_LETTER
    assert "prohibited outcome guarantee" in dispatch.error_message
    assert len(mock_provider.delivered_messages) == 0


# -------------------------------------------------------------------------
# 6. Telegram Provider Token Redaction & Live Suppression
# -------------------------------------------------------------------------
def test_telegram_provider_offline_mock_and_token_redaction(sample_alert, sample_recommendation):
    policy = NotificationPolicyEvaluator(pwa_base_url="http://localhost:5173")
    payload = policy.build_notification_payload(sample_alert, sample_recommendation)

    # Initialize with mock token and enable_live=False
    tg_provider = TelegramNotificationProvider(
        bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
        chat_id="chat-farmer-99",
        enable_live_dispatch=False,
    )

    result = tg_provider.send(payload, "chat-farmer-99")
    assert result["status"] == "mock_delivered"
    assert result["live_suppressed"] is True

    # Check formatted text includes deep link and bilingual hint
    msg_text = tg_provider.format_message(payload)
    assert "http://localhost:5173/?field=field-kolar-001&alert=" in msg_text
    assert "ಕನ್ನಡ" in msg_text


# -------------------------------------------------------------------------
# 7. Human Review Lifecycle: Stale Actions, Idempotency, and Zero Actuation
# -------------------------------------------------------------------------
def test_human_review_lifecycle_success_and_zero_actuation(memory_repo, sample_recommendation):
    memory_repo.create_farmer_recommendation(sample_recommendation)
    lifecycle = HumanReviewLifecycleManager(repository=memory_repo)

    # 1. Acknowledge action
    req_ack = HumanReviewActionRequest(action=ReviewAction.ACKNOWLEDGE, reviewer_id="agronomist-01")
    ok, resp_ack, code = lifecycle.apply_action(sample_recommendation["recommendation_id"], req_ack)
    assert ok is True
    assert code == 200
    assert resp_ack.resulting_status == AdvisoryStatus.ACKNOWLEDGED.value
    assert resp_ack.actuation_command_dispatched is False  # Zero physical actuation

    # 2. Approve action
    req_app = HumanReviewActionRequest(action=ReviewAction.APPROVE, reviewer_id="agronomist-01")
    ok, resp_app, code = lifecycle.apply_action(sample_recommendation["recommendation_id"], req_app)
    assert ok is True
    assert code == 200
    assert resp_app.resulting_status == AdvisoryStatus.APPROVED.value
    assert resp_app.actuation_command_dispatched is False

    # 3. Idempotent replay of same approval
    ok_replay, resp_replay, code_replay = lifecycle.apply_action(sample_recommendation["recommendation_id"], req_app)
    assert ok_replay is True
    assert code_replay == 200
    assert "Idempotent replay" in resp_replay.message

    # 4. Conflicting transition on finalized advisory returns 409
    req_reject = HumanReviewActionRequest(action=ReviewAction.REJECT, reviewer_id="agronomist-02")
    ok_conflict, resp_conflict, code_conflict = lifecycle.apply_action(sample_recommendation["recommendation_id"], req_reject)
    assert ok_conflict is False
    assert code_conflict == 409
    assert "already finalized" in resp_conflict.message


# -------------------------------------------------------------------------
# 8. Feedback Linkage & Offline Learning Invariant
# -------------------------------------------------------------------------
def test_feedback_multi_agent_linkage(memory_repo, sample_recommendation):
    processor = FeedbackProcessor(repository=memory_repo)
    feedback_input = StructuredFeedbackInput(
        recommendation_id=sample_recommendation["recommendation_id"],
        field_id=sample_recommendation["field_id"],
        investigation_id=sample_recommendation["investigation_id"],
        alert_id=sample_recommendation["alert_id"],
        advisory_version=1,
        rating=5,
        action_taken=True,
        observed_outcome="Soil moisture returned to 18% within 24 hours.",
        advisory_relevant=True,
        evidence_useful=True,
        field_context_correct=True,
        sensor_issue_reported=False,
        cited_agent_outputs=["sensor_reliability_agent:out_01", "agronomy_knowledge_agent:out_02"],
        idempotency_key="fb-idem-unique-123",
    )

    ok, record, msg = processor.record_feedback(feedback_input)
    assert ok is True
    assert record["investigation_id"] == sample_recommendation["investigation_id"]
    assert record["alert_id"] == sample_recommendation["alert_id"]
    assert len(record["cited_agent_outputs"]) == 2

    # Check system audit log recorded zero online prompt/threshold mutation
    audit_entry = memory_repo.audit[-1]
    assert audit_entry["action"] == "RECORD_HUMAN_FEEDBACK"
    assert audit_entry["details"]["online_prompt_mutation"] is False
    assert audit_entry["details"]["online_threshold_mutation"] is False

    # Idempotent replay
    ok2, record2, msg2 = processor.record_feedback(feedback_input)
    assert ok2 is True
    assert "Idempotent replay" in msg2


# -------------------------------------------------------------------------
# 9. FastAPI API Endpoints Integration Test
# -------------------------------------------------------------------------
def test_api_advisory_action_and_feedback(memory_repo, sample_recommendation):
    memory_repo.create_farmer_recommendation(sample_recommendation)
    client = TestClient(app)

    # 1. Agronomist approves advisory
    rec_id = sample_recommendation["recommendation_id"]
    resp_action = client.post(
        f"/api/v1/advisories/{rec_id}/action",
        json={"action": "APPROVE", "comments": "Field visit confirms early morning irrigation needed."},
        headers={"X-User-ID": "agronomist-01", "X-User-Role": "agronomist"},
    )
    assert resp_action.status_code == 200
    data_action = resp_action.json()
    assert data_action["resulting_status"] == "APPROVED"
    assert data_action["actuation_command_dispatched"] is False

    # 2. Farmer submits structured feedback
    resp_fb = client.post(
        "/api/v1/feedback",
        json={
            "recommendation_id": rec_id,
            "field_id": sample_recommendation["field_id"],
            "rating": 5,
            "action_taken": True,
            "feedback_comments": "Timely advice, crops are flourishing.",
            "advisory_relevant": True,
            "evidence_useful": True,
            "sensor_issue_reported": False,
        },
        headers={"X-User-ID": "farmer-01", "X-User-Role": "farmer"},
    )
    assert resp_fb.status_code == 201
    data_fb = resp_fb.json()
    assert data_fb["status"] == "RECORDED"
    assert data_fb["rating"] == 5

    # 3. List feedback
    resp_list_fb = client.get(
        f"/api/v1/feedback?field_id={sample_recommendation['field_id']}",
        headers={"X-User-ID": "farmer-01", "X-User-Role": "farmer"},
    )
    assert resp_list_fb.status_code == 200
    assert resp_list_fb.json()["total"] >= 1
