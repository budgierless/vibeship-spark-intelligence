"""
Chip schema validation (lightweight).

This is a minimal validator meant to keep chips safe and well-formed without
heavy dependencies. It can be extended later to full JSON Schema validation.
"""

from typing import Any, Dict, List


REQUIRED_CHIP_FIELDS = [
    "id",
    "name",
    "version",
    "description",
    "human_benefit",
    "harm_avoidance",
    "risk_level",
]

ALLOWED_RISK_LEVELS = {"low", "medium", "high"}


def validate_chip_spec(spec: Dict[str, Any]) -> List[str]:
    """Validate chip spec. Returns list of errors (empty if valid)."""
    errors: List[str] = []
    if not isinstance(spec, dict):
        return ["spec must be a dict"]

    chip = spec.get("chip")
    if not isinstance(chip, dict):
        return ["spec.chip must be a dict"]

    for field in REQUIRED_CHIP_FIELDS:
        if field not in chip or chip.get(field) in (None, ""):
            errors.append(f"missing chip.{field}")

    risk = chip.get("risk_level")
    if risk and risk not in ALLOWED_RISK_LEVELS:
        errors.append(f"invalid chip.risk_level: {risk}")

    harm_avoidance = chip.get("harm_avoidance")
    if harm_avoidance is not None and not isinstance(harm_avoidance, list):
        errors.append("chip.harm_avoidance must be a list")

    safety_tests = chip.get("safety_tests")
    if safety_tests is not None and not isinstance(safety_tests, list):
        errors.append("chip.safety_tests must be a list if provided")

    return errors


def is_valid_chip_spec(spec: Dict[str, Any]) -> bool:
    """Return True if spec passes minimal validation."""
    return len(validate_chip_spec(spec)) == 0
