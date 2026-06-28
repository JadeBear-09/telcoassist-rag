from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import Settings
from app.models import AskResponse, GuardrailReport, SourceCitation

SECRET_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{20,}|"
    r"(?:api[_-]?key|secret|token|password)\s*[:=]\s*[A-Za-z0-9_./+=-]{8,})\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
PHONE_RE = re.compile(r"(?<![A-Za-z0-9])(?:\+?\d[\d\s().-]{8,}\d)(?![A-Za-z0-9])")
CARD_CANDIDATE_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")

PROMPT_ATTACK_PATTERNS = (
    re.compile(r"\bignore (?:all )?(?:previous|prior|above|system|developer) instructions\b", re.I),
    re.compile(
        r"\b(?:reveal|show|print|dump|exfiltrate|leak).{0,40}\b"
        r"(system|developer) prompt\b",
        re.I,
    ),
    re.compile(
        r"\b(?:reveal|show|print|dump|exfiltrate|leak).{0,40}\b"
        r"(api key|secret|token)\b",
        re.I,
    ),
    re.compile(r"\b(?:jailbreak|dan mode|developer mode|disable safety|bypass guardrails)\b", re.I),
    re.compile(
        r"\b(?:model weights|training data|hidden chain[- ]of[- ]thought|system message)\b",
        re.I,
    ),
)

PHI_EXFIL_RE = re.compile(
    r"(?:\b(?:patient|diagnosis|medical record|prescription|treatment|health insurance)\b"
    r".{0,80}\b(?:export|list|show|retrieve|dump|exfiltrate)\b)"
    r"|(?:\b(?:export|list|show|retrieve|dump|exfiltrate)\b"
    r".{0,80}\b(?:patient|diagnosis|medical record|prescription|treatment|health insurance)\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FirewallCheck:
    text: str
    report: GuardrailReport


class LLMFirewall:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def inspect_question(self, question: str) -> FirewallCheck:
        token_estimate = estimate_tokens(question)
        max_tokens = max(1, self.settings.max_question_chars // 4)
        if not self.settings.guardrails_enabled:
            return FirewallCheck(
                text=question,
                report=GuardrailReport(token_estimate=token_estimate, max_tokens=max_tokens),
            )

        categories: list[str] = []
        reasons: list[str] = []

        if len(question) > self.settings.max_question_chars:
            categories.append("token_overuse")
            reasons.append(
                f"Question exceeds {self.settings.max_question_chars} character budget."
            )

        if any(pattern.search(question) for pattern in PROMPT_ATTACK_PATTERNS):
            categories.append("jailbreak_or_model_theft")
            reasons.append(
                "Prompt asks to bypass instructions, reveal hidden prompts, or steal secrets."
            )

        if PHI_EXFIL_RE.search(question):
            categories.append("phi_exfiltration")
            reasons.append("Prompt appears to request protected health information export.")

        if categories:
            return FirewallCheck(
                text=question,
                report=GuardrailReport(
                    action="block",
                    blocked=True,
                    categories=dedupe(categories),
                    reasons=dedupe(reasons),
                    token_estimate=token_estimate,
                    max_tokens=max_tokens,
                ),
            )

        sanitized, redaction_categories = redact_sensitive_text(question)
        redacted = bool(redaction_categories)
        return FirewallCheck(
            text=sanitized,
            report=GuardrailReport(
                action="redact" if redacted else "allow",
                redacted=redacted,
                categories=redaction_categories,
                reasons=(
                    ["Sensitive values were redacted before retrieval and answer generation."]
                    if redacted
                    else []
                ),
                token_estimate=token_estimate,
                max_tokens=max_tokens,
            ),
        )

    def sanitize_response(
        self,
        response: AskResponse,
        input_report: GuardrailReport,
    ) -> AskResponse:
        if not self.settings.guardrails_enabled:
            response.guardrails = input_report
            return response

        reports = [input_report]
        answer, answer_categories = redact_sensitive_text(response.answer)
        if len(answer) > self.settings.max_answer_chars:
            answer = (
                answer[: self.settings.max_answer_chars].rstrip()
                + " [TRUNCATED_BY_TOKEN_BUDGET]"
            )
            answer_categories.append("token_overuse")
        response.answer = answer

        sources: list[SourceCitation] = []
        source_categories: list[str] = []
        for source in response.sources:
            excerpt, categories = redact_sensitive_text(source.excerpt)
            source_categories.extend(categories)
            sources.append(source.model_copy(update={"excerpt": excerpt}))
        response.sources = sources

        output_categories = dedupe(answer_categories + source_categories)
        if output_categories:
            reports.append(
                GuardrailReport(
                    action="redact",
                    redacted=True,
                    categories=output_categories,
                    reasons=["Sensitive values were redacted from answer or citations."],
                    token_estimate=estimate_tokens(response.answer),
                    max_tokens=max(1, self.settings.max_answer_chars // 4),
                )
            )

        response.guardrails = merge_reports(reports)
        return response


def redact_sensitive_text(text: str) -> tuple[str, list[str]]:
    categories: list[str] = []

    redacted = SECRET_RE.sub(_mark("secret", categories), text)
    redacted = EMAIL_RE.sub(_mark("pii", categories), redacted)
    redacted = SSN_RE.sub(_mark("pii", categories), redacted)
    redacted = _redact_cards(redacted, categories)
    redacted = PHONE_RE.sub(_mark("pii", categories), redacted)

    return redacted, dedupe(categories)


def merge_reports(reports: list[GuardrailReport]) -> GuardrailReport:
    action = "allow"
    blocked = any(report.blocked for report in reports)
    redacted = any(report.redacted for report in reports)
    if blocked:
        action = "block"
    elif redacted:
        action = "redact"

    return GuardrailReport(
        action=action,
        blocked=blocked,
        redacted=redacted,
        categories=dedupe(category for report in reports for category in report.categories),
        reasons=dedupe(reason for report in reports for reason in report.reasons),
        token_estimate=max((report.token_estimate for report in reports), default=0),
        max_tokens=next((report.max_tokens for report in reports if report.max_tokens), None),
    )


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def dedupe(items) -> list[str]:
    seen = set()
    output = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _mark(category: str, categories: list[str]):
    def replace(match: re.Match[str]) -> str:
        categories.append(category)
        return f"[REDACTED_{category.upper()}]"

    return replace


def _redact_cards(text: str, categories: list[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if not _luhn_valid(digits):
            return match.group(0)
        categories.append("pci")
        return "[REDACTED_PCI]"

    return CARD_CANDIDATE_RE.sub(replace, text)


def _luhn_valid(digits: str) -> bool:
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    reverse_digits = digits[::-1]
    for idx, char in enumerate(reverse_digits):
        value = int(char)
        if idx % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0
