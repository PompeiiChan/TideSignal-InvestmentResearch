"""Session-level pending slot inheritance for multi-turn conversations."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..settings import get_settings

INHERITABLE_SLOTS_BY_INTENT: dict[str, frozenset[str]] = {
    "stock_analysis": frozenset({"stock_name", "stock_code", "industry", "analysis_dimension"}),
    "data_query": frozenset({"industry", "metric", "market", "time_range", "trade_date"}),
    "hotspot_analysis": frozenset({"topic", "industry", "event", "time_range"}),
    "document_qa": frozenset({"document_id", "stock_name", "section"}),
}

REQUIRED_SLOTS_BY_INTENT: dict[str, frozenset[str]] = {
    "stock_analysis": frozenset({"stock_name"}),
    "data_query": frozenset({"metric"}),
    "document_qa": frozenset({"document_id"}),
}

CLEAR_PENDING_INTENTS = frozenset({"chit_chat", "unknown", "prediction_request"})

SLOT_CONFIDENCE_CLARIFY_THRESHOLD = 0.55


def _slot_has_value(slots: dict[str, Any], key: str) -> bool:
    value = slots.get(key)
    if value is None:
        return False
    return bool(str(value).strip())


def _inheritable_keys(intent_id: str, pending_intent_id: str | None) -> frozenset[str]:
    current = INHERITABLE_SLOTS_BY_INTENT.get(intent_id, frozenset())
    if not pending_intent_id or pending_intent_id == intent_id:
        return current
    if pending_intent_id not in INHERITABLE_SLOTS_BY_INTENT:
        return frozenset()
    previous = INHERITABLE_SLOTS_BY_INTENT[pending_intent_id]
    return current & previous


def should_clear_pending(*, new_intent_id: str, old_intent_id: str | None = None) -> bool:
    """Return True when pending slots must be discarded for the current intent."""
    _ = old_intent_id
    return new_intent_id in CLEAR_PENDING_INTENTS


def should_persist_pending(*, intent_id: str, need_clarification: bool) -> bool:
    """Return True when a successful route should update session context_state."""
    if need_clarification:
        return False
    return intent_id in INHERITABLE_SLOTS_BY_INTENT


def merge_pending_slots(
    *,
    intent_id: str,
    pending_slots: dict[str, Any],
    extracted_slots: dict[str, Any],
    pending_intent_id: str | None = None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Merge pending slots with freshly extracted slots.

    Returns ``(merged_slots, inherited_keys, overridden_keys)``.
    """
    effective_pending: dict[str, Any] = {}
    if not should_clear_pending(new_intent_id=intent_id, old_intent_id=pending_intent_id):
        inheritable = _inheritable_keys(intent_id, pending_intent_id)
        effective_pending = {
            key: value
            for key, value in pending_slots.items()
            if key in inheritable and _slot_has_value(pending_slots, key)
        }

    merged = dict(effective_pending)
    overridden_keys: list[str] = []
    for key, value in extracted_slots.items():
        if not _slot_has_value(extracted_slots, key):
            continue
        if key in effective_pending and str(value).strip() != str(effective_pending[key]).strip():
            overridden_keys.append(key)
        merged[key] = value

    inherited_keys: list[str] = []
    for key, value in effective_pending.items():
        if key not in merged or not _slot_has_value(merged, key):
            continue
        extracted_value = extracted_slots.get(key)
        if (
            _slot_has_value(extracted_slots, key)
            and str(extracted_value).strip() != str(value).strip()
        ):
            continue
        inherited_keys.append(key)

    return merged, inherited_keys, overridden_keys


def filter_missing_after_inherit(
    missing_slots: list[str],
    merged_slots: dict[str, Any],
    inherited_keys: list[str],
) -> list[str]:
    """Drop missing slots that were inherited with a concrete value."""
    inherited = set(inherited_keys)
    return [
        name
        for name in missing_slots
        if not (name in inherited and _slot_has_value(merged_slots, name))
    ]


def build_context_state_from_run(
    *,
    intent_id: str,
    slots: dict[str, Any],
    slot_confidence: dict[str, float],
) -> dict[str, Any]:
    """Build session ``context_state`` payload after a successful routed turn."""
    inheritable = INHERITABLE_SLOTS_BY_INTENT.get(intent_id, frozenset())
    pending_slots = {
        key: slots[key] for key in inheritable if _slot_has_value(slots, key)
    }
    pending_slot_confidence = {
        key: float(slot_confidence[key])
        for key in pending_slots
        if key in slot_confidence
    }
    tz = ZoneInfo(get_settings().timezone)
    return {
        "pending_slots": pending_slots,
        "pending_intent_id": intent_id,
        "pending_slot_confidence": pending_slot_confidence,
        "updated_at": datetime.now(tz).isoformat(),
    }
