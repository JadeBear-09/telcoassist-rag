from __future__ import annotations

import argparse
import json

from app.ingestion.pipeline import run_ingestion


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest telecom documents into local and optional Qdrant indexes.")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--use-qdrant", action="store_true")
    args = parser.parse_args()

    response = run_ingestion(
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        use_qdrant=args.use_qdrant,
    )
    print(json.dumps(response.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
