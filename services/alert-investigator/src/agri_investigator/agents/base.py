"""Base class and common infrastructure for Specialist Agents in the Multi-Agent System.

Each specialist agent is an identifiable unit with a distinct role, prompt version,
input/output schema validation, and isolated execution metrics.
"""

from __future__ import annotations

import abc
import logging
import time
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ValidationError

from agri_investigator.models import AgentMessage, AgentRole, MessageType
from agri_investigator.protocol import create_agent_message

logger = logging.getLogger(__name__)


class BaseSpecialistAgent(abc.ABC):
    """Abstract base class for all specialist agents."""

    def __init__(
        self,
        role: AgentRole,
        name: str,
        version: str = "1.0.0",
        model_name: str = "gemini-2.0-flash",
        mock_mode: bool = False,
    ) -> None:
        self.role = role
        self.name = name
        self.version = version
        self.model_name = model_name
        self.mock_mode = mock_mode
        self._mock_responses: Dict[str, Dict[str, Any]] = {}

    def set_mock_response(self, scenario_key: str, response: Dict[str, Any]) -> None:
        """Sets a mock output dictionary for deterministic unit testing."""
        self._mock_responses[scenario_key] = response

    @abc.abstractmethod
    def get_input_schema(self) -> type[BaseModel]:
        """Returns the Pydantic model for input payload validation."""
        pass

    @abc.abstractmethod
    def get_output_schema(self) -> type[BaseModel]:
        """Returns the Pydantic model for output payload validation."""
        pass

    @abc.abstractmethod
    def _execute_core(self, validated_input: BaseModel) -> Tuple[BaseModel, int]:
        """Core specialist execution returning (validated_output_model, tokens_used)."""
        pass

    def process_task(self, task_msg: AgentMessage) -> Tuple[AgentMessage, float, int]:
        """Processes an incoming TASK_REQUEST or REVISION_REQUEST from the Supervisor.
        
        Returns:
            Tuple of (response_message, execution_duration_seconds, tokens_consumed).
        """
        start_time = time.perf_counter()
        tokens_used = 0

        try:
            # 1. Validate Input Schema
            input_cls = self.get_input_schema()
            validated_input = input_cls.model_validate(task_msg.payload)

            # 2. Execute Core Reasoning / Retrieval
            output_model, tokens_used = self._execute_core(validated_input)

            # 3. Formulate Output Response Message
            out_msg_type = (
                MessageType.REVISION_RESPONSE
                if task_msg.message_type == MessageType.REVISION_REQUEST
                else MessageType.TASK_RESPONSE
            )

            response_msg = create_agent_message(
                run_id=task_msg.run_id,
                correlation_id=task_msg.correlation_id,
                from_agent=self.role.value,
                to_agent=AgentRole.SUPERVISOR.value,
                message_type=out_msg_type,
                payload=output_model.model_dump(),
                parent_message_id=task_msg.message_id,
            )
            response_msg.status = "ACCEPTED"

        except Exception as exc:
            logger.error("Agent %s failed executing task: %s", self.role.value, exc, exc_info=True)
            response_msg = create_agent_message(
                run_id=task_msg.run_id,
                correlation_id=task_msg.correlation_id,
                from_agent=self.role.value,
                to_agent=AgentRole.SUPERVISOR.value,
                message_type=MessageType.ERROR_NOTIFICATION,
                payload={"error": str(exc), "agent": self.role.value},
                parent_message_id=task_msg.message_id,
            )
            response_msg.status = "ERROR"
            response_msg.error_details = {"exception_type": type(exc).__name__, "message": str(exc)}

        duration_sec = time.perf_counter() - start_time
        return response_msg, duration_sec, tokens_used

