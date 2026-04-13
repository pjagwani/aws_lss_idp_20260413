"""Python-side ALCOA+ validation and anomaly detection.

Performs deterministic checks that don't rely on the LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from . import config_loader


@dataclass
class ValidationIssue:
    principle: str       # ALCOA+ principle name
    severity: str        # low | medium | high | critical
    field: str           # field name or path
    description: str


@dataclass
class ValidationReport:
    principles: dict[str, bool] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)
    anomalies: list[ValidationIssue] = field(default_factory=list)
    null_fields: list[str] = field(default_factory=list)
    low_confidence_fields: list[tuple[str, float]] = field(default_factory=list)
    all_confidences: list[float] = field(default_factory=list)
    composite_confidence: float | None = None
    flagged_for_review: bool = False

    @property
    def pass_count(self) -> int:
        return sum(1 for v in self.principles.values() if v)

    @property
    def total_principles(self) -> int:
        return len(self.principles)


def _walk_confidences(obj: Any, prefix: str = "") -> tuple[list[float], list[tuple[str, float]], list[str]]:
    """Walk extracted data to collect confidence scores, low-confidence fields, and null fields."""
    all_conf: list[float] = []
    low_conf: list[tuple[str, float]] = []
    nulls: list[str] = []

    if isinstance(obj, dict):
        if "confidence" in obj and "value" in obj:
            c = obj["confidence"]
            if isinstance(c, (int, float)):
                all_conf.append(float(c))
                threshold = config_loader.get_nested("confidence_thresholds", "flag_for_review", default=0.70)
                if c < threshold:
                    low_conf.append((prefix, float(c)))
            if obj["value"] is None:
                nulls.append(prefix)
            return all_conf, low_conf, nulls
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            ac, lc, nl = _walk_confidences(v, p)
            all_conf.extend(ac)
            low_conf.extend(lc)
            nulls.extend(nl)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            ac, lc, nl = _walk_confidences(item, f"{prefix}[{i}]")
            all_conf.extend(ac)
            low_conf.extend(lc)
            nulls.extend(nl)
    elif obj is None and prefix:
        nulls.append(prefix)

    return all_conf, low_conf, nulls


def _has_field(data: dict, key: str) -> bool:
    """Check if a field exists and is non-null in extracted data."""
    v = data.get(key)
    if isinstance(v, dict):
        return v.get("value") is not None
    return v is not None


def _check_timestamps_contemporaneous(data: dict) -> list[ValidationIssue]:
    """Check if timestamps are within 24hr of each other and within shift hours."""
    issues = []
    cfg = config_loader.get("anomaly_detection", {})
    shift_start = cfg.get("shift_hours_start", "06:00")
    shift_end = cfg.get("shift_hours_end", "22:00")

    for key in ("start_timestamp", "end_timestamp", "mfg_date"):
        field_data = data.get(key)
        if isinstance(field_data, dict):
            val = field_data.get("value")
        else:
            val = field_data
        if not val or not isinstance(val, str):
            continue
        try:
            ts = datetime.fromisoformat(val.replace("Z", "+00:00"))
            time_str = ts.strftime("%H:%M")
            if time_str < shift_start or time_str > shift_end:
                issues.append(ValidationIssue(
                    principle="Contemporaneous",
                    severity="medium",
                    field=key,
                    description=f"Timestamp {val} is outside normal shift hours ({shift_start}-{shift_end})",
                ))
        except (ValueError, TypeError):
            pass

    # Check start < end
    start = data.get("start_timestamp")
    end = data.get("end_timestamp")
    if isinstance(start, dict):
        start = start.get("value")
    if isinstance(end, dict):
        end = end.get("value")
    if start and end and isinstance(start, str) and isinstance(end, str):
        try:
            ts_start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            ts_end = datetime.fromisoformat(end.replace("Z", "+00:00"))
            delta = (ts_end - ts_start).total_seconds()
            if delta < 0:
                issues.append(ValidationIssue(
                    principle="Contemporaneous",
                    severity="high",
                    field="start_timestamp/end_timestamp",
                    description="End timestamp is before start timestamp",
                ))
            elif delta > 86400:
                issues.append(ValidationIssue(
                    principle="Contemporaneous",
                    severity="medium",
                    field="start_timestamp/end_timestamp",
                    description=f"Process duration exceeds 24 hours ({delta/3600:.1f}h)",
                ))
        except (ValueError, TypeError):
            pass

    return issues


def _check_critical_confidence(data: dict, all_conf: list[float], prefix: str = "") -> list[ValidationIssue]:
    """Flag critical fields with confidence < threshold."""
    issues = []
    critical_threshold = config_loader.get_nested("confidence_thresholds", "critical_fields", default=0.90)
    critical_names = set(config_loader.get("critical_field_names", []))

    for key, val in data.items():
        if isinstance(val, dict) and "confidence" in val and "value" in val:
            if key in critical_names and val["confidence"] < critical_threshold:
                issues.append(ValidationIssue(
                    principle="Accurate",
                    severity="high",
                    field=key,
                    description=f"Critical field confidence {val['confidence']:.2f} < {critical_threshold}",
                ))
        elif isinstance(val, list) and key in critical_names:
            for i, item in enumerate(val):
                if isinstance(item, dict):
                    for subkey, subval in item.items():
                        if isinstance(subval, dict) and "confidence" in subval:
                            if subval["confidence"] < critical_threshold:
                                issues.append(ValidationIssue(
                                    principle="Accurate",
                                    severity="high",
                                    field=f"{key}[{i}].{subkey}",
                                    description=f"Critical field confidence {subval['confidence']:.2f} < {critical_threshold}",
                                ))
    return issues


def validate(extracted_data: dict) -> ValidationReport:
    """Run full ALCOA+ validation on extracted data. Returns a ValidationReport."""
    report = ValidationReport()

    # Get the batch_record or extracted_fields
    data = extracted_data
    if isinstance(data, dict):
        data = data.get("batch_record", data.get("extracted_fields", data))

    # Walk all confidences
    report.all_confidences, report.low_confidence_fields, report.null_fields = _walk_confidences(data)
    report.composite_confidence = (
        sum(report.all_confidences) / len(report.all_confidences)
        if report.all_confidences else None
    )

    std_threshold = config_loader.get_nested("confidence_thresholds", "standard_fields", default=0.70)
    crit_threshold = config_loader.get_nested("confidence_thresholds", "critical_fields", default=0.90)

    # --- ALCOA+ Principles ---

    # 1. Attributable
    has_operator = _has_field(data, "operator") or _has_field(data, "operator_initials")
    report.principles["Attributable"] = has_operator
    if not has_operator:
        report.issues.append(ValidationIssue("Attributable", "high", "operator", "No operator identification found"))

    # 2. Legible
    legible = all(c >= std_threshold for c in report.all_confidences) if report.all_confidences else True
    report.principles["Legible"] = legible
    for field_name, conf in report.low_confidence_fields:
        report.issues.append(ValidationIssue("Legible", "medium", field_name, f"Confidence {conf:.2f} < {std_threshold}"))

    # 3. Contemporaneous
    has_timestamp = _has_field(data, "start_timestamp") or _has_field(data, "mfg_date")
    ts_issues = _check_timestamps_contemporaneous(data)
    report.principles["Contemporaneous"] = has_timestamp and len(ts_issues) == 0
    if not has_timestamp:
        report.issues.append(ValidationIssue("Contemporaneous", "high", "timestamp", "No timestamps found"))
    report.anomalies.extend(ts_issues)

    # 4. Original
    report.principles["Original"] = True  # Source doc preserved by design

    # 5. Accurate
    crit_issues = _check_critical_confidence(data, report.all_confidences)
    accurate = len(crit_issues) == 0
    report.principles["Accurate"] = accurate
    report.issues.extend(crit_issues)

    # 6. Complete
    complete = len(report.null_fields) == 0
    report.principles["Complete"] = complete
    for nf in report.null_fields:
        report.issues.append(ValidationIssue("Complete", "medium", nf, "Field is null/missing"))

    # 7. Consistent
    llm_anomalies = extracted_data.get("anomalies", []) if isinstance(extracted_data, dict) else []
    consistent = len(llm_anomalies) == 0 and len(ts_issues) == 0
    report.principles["Consistent"] = consistent
    for a in llm_anomalies:
        if isinstance(a, str):
            report.anomalies.append(ValidationIssue("Consistent", "medium", "", a))
        elif isinstance(a, dict):
            report.anomalies.append(ValidationIssue(
                "Consistent",
                a.get("severity", "medium"),
                a.get("field", ""),
                a.get("description", str(a)),
            ))

    # 8. Enduring
    report.principles["Enduring"] = True  # Audit trail persisted to disk

    # 9. Available
    report.principles["Available"] = True  # Data accessible via UI + API

    # Flagged for review
    report.flagged_for_review = (
        not accurate
        or not legible
        or not complete
        or bool(report.anomalies)
        or (report.composite_confidence is not None and report.composite_confidence < std_threshold)
    )

    return report
