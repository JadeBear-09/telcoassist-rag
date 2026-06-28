from __future__ import annotations

import argparse
import gzip
import json
import random
import statistics
import sys
import tarfile
import time
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.embedder import hashing_embedding

COLLECTION_URL = "https://msmarco.z22.web.core.windows.net/msmarcoranking/collection.tar.gz"
QUERIES_URL = "https://msmarco.z22.web.core.windows.net/msmarcoranking/queries.tar.gz"
QRELS_DEV_URL = "https://msmarco.z22.web.core.windows.net/msmarcoranking/qrels.dev.tsv"
HF_DATASET = "sentence-transformers/msmarco"
HF_BASE_URL = f"https://huggingface.co/datasets/{HF_DATASET}/resolve/main"
HF_TREE_URL = f"https://huggingface.co/api/datasets/{HF_DATASET}/tree/main"


@dataclass(frozen=True)
class BenchmarkQuery:
    qid: int
    text: str
    relevant_pids: frozenset[int]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark MS MARCO passage retrieval with Qdrant."
    )
    parser.add_argument("--passages", type=int, required=True, help="Corpus subset size.")
    parser.add_argument("--queries", type=int, default=1000, help="Number of judged dev queries.")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--embedding-dim", type=int, default=384)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--data-dir", type=Path, default=Path("data/msmarco"))
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("data/processed/msmarco_benchmark"),
    )
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--collection-prefix", default="msmarco_passages")
    parser.add_argument(
        "--source",
        choices=["hf", "official"],
        default="hf",
        help="Use Hugging Face parquet mirror or official MS MARCO tarballs.",
    )
    parser.add_argument("--recreate", action="store_true")
    parser.add_argument(
        "--candidate-pid-max",
        type=int,
        default=None,
        help="Only choose qrels whose positive pids are below this id. Default: max(passages, 1M).",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download/cache MS MARCO files and exit.",
    )
    args = parser.parse_args()

    args.data_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    qrels_path = args.data_dir / "qrels.dev.tsv"
    download_if_missing(QRELS_DEV_URL, qrels_path)
    if args.download_only:
        paths = (
            download_sources(args.data_dir)
            if args.source == "official"
            else download_hf_sources(args.data_dir)
        )
        print(json.dumps({name: str(path) for name, path in paths.items()}, indent=2))
        return

    candidate_pid_max = args.candidate_pid_max or max(args.passages, 1_000_000)
    qrels_by_qid = read_qrels(qrels_path, candidate_pid_max)
    if args.source == "official":
        paths = download_sources(args.data_dir)
        queries_by_qid = read_dev_queries(paths["queries"])
    else:
        paths = download_hf_sources(args.data_dir)
        queries_by_qid = read_dev_queries(paths["queries"])
    benchmark_queries = select_queries(
        qrels_by_qid=qrels_by_qid,
        queries_by_qid=queries_by_qid,
        count=args.queries,
        seed=args.seed,
    )
    selected_pids = select_passage_ids(
        benchmark_queries=benchmark_queries,
        passages=args.passages,
    )
    corpus_path = (
        args.data_dir
        / f"{args.source}_passages_{args.passages}_q{args.queries}_s{args.seed}.jsonl.gz"
    )
    if args.source == "official":
        build_official_subset(
            collection_path=paths["collection"],
            output_path=corpus_path,
            selected_pids=selected_pids,
        )
    else:
        build_hf_subset(
            data_dir=args.data_dir,
            output_path=corpus_path,
            selected_pids=selected_pids,
        )

    from qdrant_client import QdrantClient, models

    client = QdrantClient(url=args.qdrant_url, timeout=120)
    collection_name = f"{args.collection_prefix}_{args.passages}"
    recreate_collection(
        client=client,
        models=models,
        collection_name=collection_name,
        vector_size=args.embedding_dim,
        recreate=args.recreate,
    )

    indexed_count, index_seconds = index_corpus(
        client=client,
        models=models,
        collection_name=collection_name,
        corpus_path=corpus_path,
        embedding_dim=args.embedding_dim,
        batch_size=args.batch_size,
    )
    metrics = run_queries(
        client=client,
        collection_name=collection_name,
        benchmark_queries=benchmark_queries,
        embedding_dim=args.embedding_dim,
        top_k=args.top_k,
    )
    result = {
        "passages": args.passages,
        "queries": len(benchmark_queries),
        "top_k": args.top_k,
        "collection": collection_name,
        "embedding": {
            "provider": "hashing",
            "dim": args.embedding_dim,
        },
        "source": args.source,
        "qdrant_url": args.qdrant_url,
        "candidate_pid_max": candidate_pid_max,
        "indexed_count": indexed_count,
        "index_seconds": round(index_seconds, 2),
        "index_passages_per_second": round(indexed_count / index_seconds, 2)
        if index_seconds
        else 0.0,
        **metrics,
    }
    result_path = args.results_dir / f"msmarco_qdrant_{args.passages}.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def download_sources(data_dir: Path) -> dict[str, Path]:
    paths = {
        "collection": data_dir / "collection.tar.gz",
        "queries": data_dir / "queries.tar.gz",
        "qrels": data_dir / "qrels.dev.tsv",
    }
    download_if_missing(COLLECTION_URL, paths["collection"])
    download_if_missing(QUERIES_URL, paths["queries"])
    download_if_missing(QRELS_DEV_URL, paths["qrels"])
    return paths


def download_hf_sources(data_dir: Path) -> dict[str, Path]:
    paths = {
        "queries": data_dir / "queries.tar.gz",
        "qrels": data_dir / "qrels.dev.tsv",
    }
    download_if_missing(QUERIES_URL, paths["queries"])
    download_if_missing(QRELS_DEV_URL, paths["qrels"])
    return paths


def download_if_missing(url: str, path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    print(f"downloading {url} -> {path}", file=sys.stderr)
    with urllib.request.urlopen(url) as response, tmp_path.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    tmp_path.replace(path)


def read_qrels(path: Path, candidate_pid_max: int) -> dict[int, set[int]]:
    qrels_by_qid: dict[int, set[int]] = defaultdict(set)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            qid, _, pid, relevance = line.rstrip("\n").split("\t")
            if int(relevance) <= 0:
                continue
            passage_id = int(pid)
            if passage_id < candidate_pid_max:
                qrels_by_qid[int(qid)].add(passage_id)
    return dict(qrels_by_qid)


def read_dev_queries(path: Path) -> dict[int, str]:
    queries: dict[int, str] = {}
    with tarfile.open(path, "r:gz") as archive:
        member = find_query_member(archive)
        extracted = archive.extractfile(member)
        if extracted is None:
            raise RuntimeError(f"could not extract {member.name}")
        for raw_line in extracted:
            qid, query = raw_line.decode("utf-8").rstrip("\n").split("\t", 1)
            queries[int(qid)] = query
    return queries


def read_hf_queries(path: Path) -> dict[int, str]:
    import pyarrow.parquet as pq

    table = pq.read_table(path, columns=["query_id", "query"])
    query_ids = table.column("query_id").to_pylist()
    query_texts = table.column("query").to_pylist()
    return {int(qid): str(query) for qid, query in zip(query_ids, query_texts, strict=True)}


def find_query_member(archive: tarfile.TarFile) -> tarfile.TarInfo:
    for member in archive.getmembers():
        name = Path(member.name).name
        if name in {"queries.dev.tsv", "queries.dev.small.tsv"}:
            return member
    for member in archive.getmembers():
        name = Path(member.name).name
        if name.startswith("queries.dev") and name.endswith(".tsv"):
            return member
    names = ", ".join(member.name for member in archive.getmembers())
    raise RuntimeError(f"dev queries TSV not found in archive; members: {names}")


def select_queries(
    qrels_by_qid: dict[int, set[int]],
    queries_by_qid: dict[int, str],
    count: int,
    seed: int,
) -> list[BenchmarkQuery]:
    eligible = [
        qid
        for qid, relevant_pids in qrels_by_qid.items()
        if relevant_pids and qid in queries_by_qid
    ]
    if len(eligible) < count:
        raise RuntimeError(
            f"only {len(eligible)} eligible judged queries available; requested {count}"
        )
    eligible = sorted(eligible)
    random.Random(seed).shuffle(eligible)
    selected_qids = eligible[:count]
    return [
        BenchmarkQuery(
            qid=qid,
            text=queries_by_qid[qid],
            relevant_pids=frozenset(qrels_by_qid[qid]),
        )
        for qid in selected_qids
    ]


def select_passage_ids(
    benchmark_queries: list[BenchmarkQuery],
    passages: int,
) -> set[int]:
    selected: set[int] = set()
    for query in benchmark_queries:
        selected.update(query.relevant_pids)
    if len(selected) > passages:
        raise RuntimeError(
            f"{len(selected)} relevant passages required, above requested corpus size {passages}"
        )
    pid = 0
    while len(selected) < passages:
        selected.add(pid)
        pid += 1
    return selected


def build_official_subset(
    collection_path: Path,
    output_path: Path,
    selected_pids: set[int],
) -> None:
    if output_path.exists() and count_jsonl_gz(output_path) == len(selected_pids):
        return
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    remaining = set(selected_pids)
    with tarfile.open(collection_path, "r:gz") as archive:
        member = find_collection_member(archive)
        extracted = archive.extractfile(member)
        if extracted is None:
            raise RuntimeError(f"could not extract {member.name}")
        with gzip.open(tmp_path, "wt", encoding="utf-8") as output:
            for raw_line in extracted:
                pid_text, passage = raw_line.decode("utf-8").rstrip("\n").split("\t", 1)
                pid = int(pid_text)
                if pid not in remaining:
                    continue
                output.write(json.dumps({"pid": pid, "text": passage}) + "\n")
                remaining.remove(pid)
                if not remaining:
                    break
    if remaining:
        sample = sorted(remaining)[:10]
        raise RuntimeError(f"missing {len(remaining)} selected passages, sample={sample}")
    tmp_path.replace(output_path)


def build_hf_subset(data_dir: Path, output_path: Path, selected_pids: set[int]) -> None:
    if output_path.exists() and count_jsonl_gz(output_path) == len(selected_pids):
        return

    import pyarrow.parquet as pq

    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    remaining = set(selected_pids)
    with gzip.open(tmp_path, "wt", encoding="utf-8") as output:
        for remote_path in list_hf_parquet_files("corpus"):
            local_path = data_dir / "hf" / remote_path
            download_if_missing(f"{HF_BASE_URL}/{remote_path}", local_path)
            parquet_file = pq.ParquetFile(local_path)
            for batch in parquet_file.iter_batches(
                batch_size=65_536,
                columns=["passage_id", "passage"],
            ):
                passage_ids = batch.column("passage_id").to_pylist()
                passages = batch.column("passage").to_pylist()
                for raw_pid, passage in zip(passage_ids, passages, strict=True):
                    pid = int(raw_pid)
                    if pid not in remaining:
                        continue
                    output.write(json.dumps({"pid": pid, "text": str(passage)}) + "\n")
                    remaining.remove(pid)
                if not remaining:
                    break
            if not remaining:
                break
    if remaining:
        sample = sorted(remaining)[:10]
        raise RuntimeError(f"missing {len(remaining)} selected passages, sample={sample}")
    tmp_path.replace(output_path)


def list_hf_parquet_files(prefix: str) -> list[str]:
    with urllib.request.urlopen(f"{HF_TREE_URL}/{prefix}") as response:
        rows = json.load(response)
    return sorted(
        row["path"]
        for row in rows
        if row.get("type") == "file" and str(row.get("path", "")).endswith(".parquet")
    )


def find_collection_member(archive: tarfile.TarFile) -> tarfile.TarInfo:
    for member in archive.getmembers():
        if Path(member.name).name == "collection.tsv":
            return member
    names = ", ".join(member.name for member in archive.getmembers())
    raise RuntimeError(f"collection.tsv not found in archive; members: {names}")


def count_jsonl_gz(path: Path) -> int:
    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for _ in handle:
            count += 1
    return count


def recreate_collection(
    client,
    models,
    collection_name: str,
    vector_size: int,
    recreate: bool,
) -> None:
    if client.collection_exists(collection_name):
        if not recreate:
            return
        client.delete_collection(collection_name, timeout=120)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        on_disk_payload=True,
    )


def index_corpus(
    client,
    models,
    collection_name: str,
    corpus_path: Path,
    embedding_dim: int,
    batch_size: int,
) -> tuple[int, float]:
    started = time.perf_counter()
    indexed = 0
    batch: list[dict[str, str | int]] = []
    for row in iter_jsonl_gz(corpus_path):
        batch.append(row)
        if len(batch) >= batch_size:
            indexed += upsert_batch(client, models, collection_name, batch, embedding_dim)
            batch.clear()
            if indexed % 10_000 == 0:
                print(f"indexed {indexed}", file=sys.stderr)
    if batch:
        indexed += upsert_batch(client, models, collection_name, batch, embedding_dim)
    return indexed, time.perf_counter() - started


def iter_jsonl_gz(path: Path) -> Iterable[dict[str, str | int]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def upsert_batch(
    client,
    models,
    collection_name: str,
    rows: list[dict[str, str | int]],
    embedding_dim: int,
) -> int:
    points = []
    for row in rows:
        text = str(row["text"])
        pid = int(row["pid"])
        points.append(
            models.PointStruct(
                id=pid,
                vector=hashing_embedding(text, embedding_dim),
                payload={"pid": pid, "text": text},
            )
        )
    client.upsert(collection_name=collection_name, points=points, wait=True)
    return len(points)


def run_queries(
    client,
    collection_name: str,
    benchmark_queries: list[BenchmarkQuery],
    embedding_dim: int,
    top_k: int,
) -> dict[str, float]:
    latencies_ms: list[float] = []
    recall_sum = 0.0
    reciprocal_rank_sum = 0.0

    for index, query in enumerate(benchmark_queries, start=1):
        started = time.perf_counter()
        vector = hashing_embedding(query.text, embedding_dim)
        hits = client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=top_k,
            with_payload=["pid"],
            with_vectors=False,
        )
        latencies_ms.append((time.perf_counter() - started) * 1000)

        retrieved_pids = [int(hit.payload["pid"]) for hit in hits]
        relevant = query.relevant_pids
        relevant_hits = [pid for pid in retrieved_pids if pid in relevant]
        recall_sum += len(set(relevant_hits)) / len(relevant)
        first_rank = next(
            (rank for rank, pid in enumerate(retrieved_pids, start=1) if pid in relevant),
            None,
        )
        if first_rank is not None and first_rank <= top_k:
            reciprocal_rank_sum += 1.0 / first_rank
        if index % 100 == 0:
            print(f"queried {index}", file=sys.stderr)

    return {
        f"recall_at_{top_k}": round(recall_sum / len(benchmark_queries), 4),
        f"mrr_at_{top_k}": round(reciprocal_rank_sum / len(benchmark_queries), 4),
        "latency_ms_p50": round(statistics.median(latencies_ms), 2),
        "latency_ms_p95": round(percentile(latencies_ms, 95), 2),
        "latency_ms_avg": round(statistics.fmean(latencies_ms), 2),
    }


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    rank = (len(ordered) - 1) * (pct / 100)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


if __name__ == "__main__":
    main()
