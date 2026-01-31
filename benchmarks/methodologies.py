from typing import Dict, List

from lib.promoter import is_operational_insight, is_unsafe_insight


KEYWORDS_CORRECTION = ["actually", "no", "not", "meant", "instead", "rather"]
KEYWORDS_WHY = ["because", "so that", "in order to", "reason", "why"]
KEYWORDS_PREF = ["prefer", "rather", "instead", "go with", "use", "choose"]


def _contains_any(text: str, keywords: List[str]) -> bool:
    text = (text or "").lower()
    return any(k in text for k in keywords)


def method_baseline(record: Dict) -> bool:
    return True


def method_operational_filter(record: Dict) -> bool:
    return not is_operational_insight(record.get("insight", ""))


def method_safety_filter(record: Dict) -> bool:
    return not is_unsafe_insight(record.get("insight", ""))


def method_outcome_required(record: Dict) -> bool:
    return record.get("outcome") is not None


def method_min_fields_2(record: Dict) -> bool:
    return record.get("fields_count", 0) >= 2


def method_high_conf(record: Dict) -> bool:
    return record.get("confidence", 0.0) >= 0.8


def method_correction_first(record: Dict) -> bool:
    return _contains_any(record.get("event_text", ""), KEYWORDS_CORRECTION)


def method_why_capture(record: Dict) -> bool:
    return _contains_any(record.get("event_text", ""), KEYWORDS_WHY)


def method_preference_only(record: Dict) -> bool:
    return _contains_any(record.get("event_text", ""), KEYWORDS_PREF)


def method_balanced(record: Dict) -> bool:
    if is_operational_insight(record.get("insight", "")):
        return False
    if is_unsafe_insight(record.get("insight", "")):
        return False
    if record.get("confidence", 0.0) < 0.7:
        return False
    return record.get("outcome") is not None or record.get("fields_count", 0) >= 2


def get_methodologies() -> List[Dict]:
    return [
        {
            "id": "baseline",
            "description": "Accept all insights (no filtering).",
            "accept": method_baseline,
        },
        {
            "id": "operational_filter",
            "description": "Reject operational telemetry (tool sequences, usage counts).",
            "accept": method_operational_filter,
        },
        {
            "id": "safety_filter",
            "description": "Reject unsafe or harmful insight text.",
            "accept": method_safety_filter,
        },
        {
            "id": "outcome_required",
            "description": "Only accept insights with matched outcomes.",
            "accept": method_outcome_required,
        },
        {
            "id": "min_fields_2",
            "description": "Require at least 2 captured fields.",
            "accept": method_min_fields_2,
        },
        {
            "id": "high_conf_0_8",
            "description": "Require confidence >= 0.8.",
            "accept": method_high_conf,
        },
        {
            "id": "correction_first",
            "description": "Only accept insights from correction-like user input.",
            "accept": method_correction_first,
        },
        {
            "id": "why_capture",
            "description": "Only accept insights when a causal reason is present.",
            "accept": method_why_capture,
        },
        {
            "id": "preference_only",
            "description": "Only accept preference-related signals.",
            "accept": method_preference_only,
        },
        {
            "id": "balanced",
            "description": "Operational + safety filter + confidence >= 0.7 + evidence or outcome.",
            "accept": method_balanced,
        },
    ]
