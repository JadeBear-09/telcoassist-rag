from __future__ import annotations

import argparse
import random
from pathlib import Path


TOPICS = [
    ("5G troubleshooting SOP", "5G", "Network Support"),
    ("SIM activation policy", "SIM", "Support"),
    ("eSIM migration guide", "eSIM", "Support"),
    ("billing dispute process", "Billing", "Billing Operations"),
    ("outage escalation runbook", "Network", "Network Operations"),
    ("GDPR privacy compliance note", "Privacy", "Compliance"),
]

REGIONS = ["Germany", "United States", "Global"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic telecom documents for RAG demos.")
    parser.add_argument("--docs", type=int, default=500)
    parser.add_argument("--out", default="data/raw")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    for index in range(args.docs):
        topic, product, department = random.choice(TOPICS)
        region = random.choice(REGIONS)
        doc_id = f"DT_SYN_{index:06d}"
        body = synthetic_body(doc_id, topic, product, department, region)
        path = out_dir / f"{doc_id}_{topic.lower().replace(' ', '_')}.md"
        path.write_text(body, encoding="utf-8")


def synthetic_body(doc_id: str, topic: str, product: str, department: str, region: str) -> str:
    return f"""# {topic}

Document ID: {doc_id}
Department: {department}
Region: {region}
Product: {product}

## Purpose
This document defines telecom support guidance for {product} cases in {region}.

## Procedure
1. Verify customer account status, service entitlement, and recent order or SIM changes.
2. Check device compatibility, provisioning state, APN profile, and known incident windows.
3. Use metadata filters for region, product, department, and access level before retrieval.
4. Escalate to the owning L2 team when frontline checks do not resolve the issue.

## Quality Notes
Support answers must cite source chunks and avoid unsupported claims.
"""


if __name__ == "__main__":
    main()
