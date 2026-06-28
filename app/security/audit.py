from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from app.models import AuditAction, AuditLogRecord, GuardrailMetrics, RequestIdentity
from app.security.llm_firewall import redact_sensitive_text

AUDIT_FILE = "audit.jsonl"


def audit_path(data_dir: Path) -> Path:
    return data_dir / "audit" / AUDIT_FILE


def question_hash(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def build_audit_record(
    *,
    request_id: str,
    route: str,
    identity: RequestIdentity,
    question: str,
    action: AuditAction,
    guardrail_categories: list[str],
    retrieved_doc_ids: list[str],
    latency_ms: int,
    insufficient_information: bool,
    confidence: float,
) -> AuditLogRecord:
    return AuditLogRecord(
        request_id=safe_log_value(request_id) or "",
        timestamp=datetime.now(UTC),
        route=route,
        tenant_id=safe_log_value(identity.tenant_id),
        user_id=safe_log_value(identity.user_id),
        roles=[value for value in (safe_log_value(role) for role in identity.roles) if value],
        question_hash=question_hash(question),
        action=action,
        guardrail_categories=[
            value
            for value in (safe_log_value(category) for category in guardrail_categories)
            if value
        ],
        retrieved_doc_ids=[
            value for value in (safe_log_value(doc_id) for doc_id in retrieved_doc_ids) if value
        ],
        latency_ms=max(0, latency_ms),
        insufficient_information=insufficient_information,
        confidence=confidence,
    )


def append_audit_record(data_dir: Path, record: AuditLogRecord) -> None:
    path = audit_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")


def read_audit_records(data_dir: Path) -> list[AuditLogRecord]:
    path = audit_path(data_dir)
    if not path.exists():
        return []

    records: list[AuditLogRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                records.append(AuditLogRecord.model_validate_json(line))
            except (json.JSONDecodeError, ValidationError):
                continue
    return records


def aggregate_guardrail_metrics(data_dir: Path) -> GuardrailMetrics:
    records = read_audit_records(data_dir)
    total = len(records)
    if total == 0:
        return GuardrailMetrics()

    blocked = sum(1 for record in records if record.action == "block")
    sensitive_categories = {"pii", "pci", "secret"}
    redacted = sum(
        1
        for record in records
        if record.action == "redact"
        or bool(sensitive_categories.intersection(record.guardrail_categories))
    )
    insufficient = sum(1 for record in records if record.insufficient_information)
    category_counts = Counter(
        category for record in records for category in record.guardrail_categories
    )
    avg_latency = sum(record.latency_ms for record in records) / total

    return GuardrailMetrics(
        total_requests=total,
        blocked_requests=blocked,
        redacted_requests=redacted,
        block_rate=round(blocked / total, 4),
        redaction_rate=round(redacted / total, 4),
        category_counts=dict(category_counts),
        insufficient_information_rate=round(insufficient / total, 4),
        avg_latency_ms=round(avg_latency, 2),
    )


def safe_log_value(value: str | None) -> str | None:
    if value is None:
        return None
    redacted, categories = redact_sensitive_text(value)
    return "[REDACTED]" if categories else redacted
