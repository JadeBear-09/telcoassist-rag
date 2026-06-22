from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.models import DocumentMetadata


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    metadata: DocumentMetadata


def parse_document(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8")
    elif suffix == ".csv":
        text = _parse_csv(path)
    elif suffix == ".pdf":
        text = _parse_pdf(path)
    else:
        raise ValueError(f"Unsupported document type: {path.suffix}")

    cleaned = clean_text(text)
    metadata = infer_metadata(path, cleaned)
    return ParsedDocument(text=cleaned, metadata=metadata)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def infer_metadata(path: Path, text: str) -> DocumentMetadata:
    name = path.stem.replace("_", " ").replace("-", " ").title()
    lowered = f"{path.name} {text[:3000]}".lower()

    product = _extract_field(text, "Product") or "General"
    if "5g" in lowered:
        product = product if product != "General" else "5G"
    elif "esim" in lowered:
        product = product if product != "General" else "eSIM"
    elif "sim" in lowered:
        product = product if product != "General" else "SIM"
    elif "billing" in lowered or "invoice" in lowered:
        product = product if product != "General" else "Billing"
    elif "fiber" in lowered:
        product = product if product != "General" else "Fiber"

    department = _extract_field(text, "Department") or "Support"
    if "network" in lowered or "tower" in lowered or "outage" in lowered:
        department = department if department != "Support" else "Network Operations"
    elif "billing" in lowered:
        department = department if department != "Support" else "Billing Operations"
    elif "privacy" in lowered or "gdpr" in lowered or "compliance" in lowered:
        department = department if department != "Support" else "Compliance"
    elif "sales" in lowered or "retention" in lowered:
        department = department if department != "Support" else "Sales"

    doc_type = "Knowledge Base"
    if "sop" in lowered or "procedure" in lowered:
        doc_type = "SOP"
    elif "policy" in lowered:
        doc_type = "Policy"
    elif "runbook" in lowered or "escalation" in lowered:
        doc_type = "Runbook"
    elif "rca" in lowered or "incident" in lowered:
        doc_type = "Incident Report"

    region = _extract_field(text, "Region") or "Global"
    if "berlin" in lowered or "germany" in lowered or "deutsche telekom" in lowered:
        region = region if region != "Global" else "Germany"
    elif "us" in lowered or "t-mobile" in lowered:
        region = region if region != "Global" else "United States"

    explicit_id = re.search(r"(?im)^Document ID:\s*([A-Z0-9_-]+)\s*$", text)
    doc_id = explicit_id.group(1) if explicit_id else _stable_doc_id(path, product, doc_type)
    company = _extract_field(text, "Company") or ("Deutsche Telekom" if region == "Germany" else "T-Mobile")
    access_level = _extract_field(text, "Access Level") or "support_agent"
    return DocumentMetadata(
        doc_id=doc_id,
        title=name,
        company=company,
        department=department,
        region=region,
        doc_type=doc_type,
        product=product,
        created_at=date(2025, 11, 10),
        access_level=access_level,
        source_path=str(path),
    )


def _parse_csv(path: Path) -> str:
    rows: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append("; ".join(f"{key}: {value}" for key, value in row.items()))
    return "\n".join(rows)


def _parse_pdf(path: Path) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Install pymupdf to parse PDF documents.") from exc

    pages: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            pages.append(page.get_text())
    return "\n".join(pages)


def _extract_field(text: str, field_name: str) -> str | None:
    pattern = rf"(?im)^{re.escape(field_name)}:\s*(.+?)\s*$"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def _stable_doc_id(path: Path, product: str, doc_type: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", path.stem).strip("_").upper()
    product_code = re.sub(r"[^A-Za-z0-9]+", "", product).upper()[:8] or "GEN"
    type_code = re.sub(r"[^A-Za-z0-9]+", "", doc_type).upper()[:6] or "DOC"
    digest = int(hashlib.sha1(path.stem.encode("utf-8")).hexdigest()[:8], 16) % 10000
    return f"DT_{product_code}_{type_code}_{digest:04d}_{slug[:18]}"
