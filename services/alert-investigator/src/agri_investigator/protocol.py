"""Communication protocol, message creation, validation, and idempotency handling.

Ensures that every agent interaction is mediated through strongly typed, versioned
AgentMessage envelopes with correlation tracking and duplicate rejection.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set
from pydantic import ValidationError

from agri_investigator.models import AgentMessage, AgentRole, MessageType


class InvalidMessageError(ValueError):
    """Raised when an AgentMessage fails schema or routing validation."""
    pass


class DuplicateMessageError(ValueError):
    """Raised when an idempotency key collides with a previously processed message."""
    pass


def generate_idempotency_key(
    run_id: str,
    from_agent: str,
    to_agent: str,
    message_type: str,
    payload: Dict[str, Any],
    parent_message_id: Optional[str] = None,
    revision_count: int = 0,
) -> str:
    """Generates a deterministic idempotency key from message routing, parent, cycle, and payload."""
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    raw = f"{run_id}:{parent_message_id or 'root'}:rev{revision_count}:{from_agent}:{to_agent}:{message_type}:{payload_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def create_agent_message(
    run_id: str,
    correlation_id: str,
    from_agent: str,
    to_agent: str,
    message_type: MessageType,
    payload: Dict[str, Any],
    parent_message_id: Optional[str] = None,
    deadline: Optional[datetime] = None,
    idempotency_key: Optional[str] = None,
    revision_count: int = 0,
) -> AgentMessage:
    """Constructs a validated, versioned AgentMessage."""
    if not idempotency_key:
        idempotency_key = generate_idempotency_key(
            run_id=run_id,
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type.value,
            payload=payload,
            parent_message_id=parent_message_id,
            revision_count=revision_count,
        )

    msg = AgentMessage(
        message_id=str(uuid.uuid4()),
        run_id=run_id,
        correlation_id=correlation_id,
        parent_message_id=parent_message_id,
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=message_type,
        payload_schema_version="1.0.0",
        payload=payload,
        created_at=datetime.now(timezone.utc),
        deadline=deadline,
        idempotency_key=idempotency_key,
        status="ACCEPTED",
    )
    return msg


class MessageRouter:
    """Tracks processed message idempotency keys and validates routing rules."""

    def __init__(self) -> None:
        self._processed_keys: Set[str] = set()

    def check_and_register(self, message: AgentMessage) -> None:
        """Verifies idempotency; raises DuplicateMessageError if already processed."""
        if message.idempotency_key in self._processed_keys:
            raise DuplicateMessageError(
                f"Duplicate message detected with idempotency_key '{message.idempotency_key}'."
            )
        self._processed_keys.add(message.idempotency_key)

    def validate_message(self, message: AgentMessage) -> None:
        """Validates routing constraints and non-empty payload."""
        # Supervisor must be one of the participants
        if message.from_agent != AgentRole.SUPERVISOR.value and message.to_agent != AgentRole.SUPERVISOR.value:
            raise InvalidMessageError(
                f"Direct agent-to-agent communication ({message.from_agent} -> {message.to_agent}) "
                f"is strictly prohibited. All communication must route through the Supervisor."
            )

        if not message.payload:
            raise InvalidMessageError("AgentMessage payload cannot be empty.")
