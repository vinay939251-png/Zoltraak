"""
Event contract validation and schema enforcement for Kafka streaming topics.
Adheres strictly to data-platform/events/contracts.json and Section 7.3 specifications.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

CONTRACTS_FILE = Path(__file__).resolve().parent.parent.parent / "data-platform" / "events" / "contracts.json"

PROTECTED_ATTRIBUTES = {
    "gender", "sex", "marital_status", "marital", "race", "ethnicity",
    "religion", "creed", "nationality", "citizenship", "sexual_orientation",
    "disability", "accent", "vulnerability_score", "household_size"
}


class EventContractValidationError(ValueError):
    """Raised when an event payload fails contract validation."""
    pass


class EventContractRegistry:
    """Loads and validates Kafka events against registered contracts."""

    def __init__(self, contracts_path: Optional[Path] = None):
        self.path = contracts_path or CONTRACTS_FILE
        self._schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        if not self.path.exists():
            raise FileNotFoundError(f"Contracts file not found at: {self.path}")
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def common_fields(self) -> List[str]:
        return self._schema.get("common", [])

    @property
    def registered_events(self) -> List[str]:
        return list(self._schema.get("events", {}).keys())

    def get_event_fields(self, event_type: str) -> List[str]:
        return self._schema.get("events", {}).get(event_type, [])

    def validate(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates event structure, common fields, event-specific fields, and protected attributes.
        Returns (is_valid, error_message).
        """
        if not isinstance(payload, dict):
            return False, "Payload must be a dictionary"

        event_type = payload.get("eventType")
        if not event_type:
            return False, "Missing mandatory field 'eventType'"

        if event_type not in self._schema.get("events", {}):
            return False, f"Unknown or unregistered eventType '{event_type}'"

        # Check common headers
        for field in self.common_fields:
            if field not in payload or payload[field] is None:
                return False, f"Missing mandatory common field '{field}' for eventType '{event_type}'"

        # Check event-specific required fields
        required_fields = self.get_event_fields(event_type)
        for field in required_fields:
            if field not in payload or payload[field] is None:
                return False, f"Missing mandatory field '{field}' for eventType '{event_type}'"

        # Check for forbidden protected attributes (anti-bias protection)
        for key in payload.keys():
            if key.lower() in PROTECTED_ATTRIBUTES:
                return False, f"Payload contains prohibited protected attribute '{key}'"

        return True, None

    def create_event(
        self,
        event_type: str,
        source_system: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        event_id: Optional[str] = None,
        occurred_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Factory helper to build a well-formed, compliant Kafka event payload.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        event = {
            "eventId": event_id or f"evt-{uuid.uuid4().hex[:12]}",
            "eventType": event_type,
            "occurredAt": occurred_at or now_iso,
            "ingestedAt": now_iso,
            "sourceSystem": source_system,
            "correlationId": correlation_id or f"corr-{uuid.uuid4().hex[:8]}",
            **data
        }

        is_valid, error = self.validate(event)
        if not is_valid:
            raise EventContractValidationError(error)

        return event


# Global registry singleton
registry = EventContractRegistry()
