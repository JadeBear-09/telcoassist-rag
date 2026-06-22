from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.evaluation.eval_retrieval import evaluate_retrieval


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval against golden telecom Q&A rows.")
    parser.add_argument("--golden", default="data/golden_questions.csv")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()

    metrics = evaluate_retrieval(Path(args.golden), top_k=args.top_k, processed_dir=Path(args.processed_dir))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
