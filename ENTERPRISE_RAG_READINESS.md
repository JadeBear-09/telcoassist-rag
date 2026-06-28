# TelcoAssist Enterprise RAG Readiness Notes

Goal: explain what TelcoAssist already has, what real enterprise RAG still needs, how to rebuild each missing piece, and how to answer interview edge-case questions honestly.

## Honest Positioning

TelcoAssist is a production-style telecom RAG prototype, not a complete enterprise RAG platform yet.

Good current claims:

- Built FastAPI RAG backend for telecom SOPs, runbooks, policy docs, and support questions.
- Implemented parsing, metadata extraction, chunking, embeddings, hybrid retrieval, reranking, citations, confidence scoring, and insufficient-context fallback.
- Added ZIP upload for demo/admin ingestion.
- Added golden-question retrieval evaluation.
- Added feedback capture API with JSONL storage.
- Added Prompt Lab API comparing baseline vs candidate style/template prompts on golden questions.
- Added lightweight LLM firewall for jailbreak/model-theft/PHI-exfil blocking, PII/PCI/secret redaction, token budgets, and per-request user OpenAI keys.
- Added app-layer ACL-before-retrieval using demo tenant/user/role headers, ACL metadata, local/BM25/Qdrant filtering, sanitized audit JSONL, and guardrail metrics.
- Benchmarked Qdrant at 1M-passage scale using MS MARCO, measuring indexing throughput and p50/p95 query latency.
- Designed AWS production shape using S3, SQS, ECS/Fargate workers, Qdrant, CloudWatch, and Cognito.

Bad or dishonest claims:

- Do not claim 1M private Telekom documents.
- Do not claim production enterprise security is complete.
- Do not claim HIPAA/PCI compliance from regex redaction alone.
- Do not claim model theft/jailbreak prevention is perfect.
- Do not claim prompt or RAG quality is SOTA.
- Do not claim feedback reviewer UI, prompt publish gates, or CI quality gates are complete.
- Do not claim model fine-tuning unless training jobs and evaluation exist.

Best interview line:

```text
TelcoAssist is a production-style telecom RAG prototype. It proves the core retrieval, citation, fallback, upload, evaluation, feedback capture, Prompt Lab, lightweight LLM firewall, ACL-before-retrieval, sanitized audit logs, guardrail metrics, and scale-benchmarking path. For real enterprise rollout, I would replace demo identity headers with OIDC/JWT auth, move local audit JSONL into immutable managed storage/SIEM, add provider-grade DLP, encrypted BYOK storage, reviewer workflows, prompt publish gates, async cloud ingestion, stronger embeddings/rerankers, faithfulness evaluation, provenance UI, monitoring, and CI regression gates.
```

## Research Map

This project follows core RAG ideas, but uses pragmatic engineering rather than copying one paper end-to-end.

| Idea | Paper / Pattern | Current repo status |
| --- | --- | --- |
| Retrieve external knowledge before answering | RAG, Lewis et al. 2020 | Yes: chunks, retriever, generator |
| Dense vector retrieval | DPR, Karpukhin et al. 2020 | Yes: embeddings + Qdrant/local index |
| Lexical + vector hybrid retrieval | Common production search pattern | Yes: BM25 + vector + RRF |
| Reranking | Cross-encoder reranker pattern | Partial: lexical fallback, no real cross-encoder yet |
| Grounded answer evaluation | RAGAS / faithfulness eval pattern | Partial: retrieval eval + citation proxy only |
| Self-critique / adaptive retrieval | Self-RAG style | Not implemented |
| Human feedback improvement | RAG ops pattern | Partial: `/feedback` JSONL capture exists |

Architecture answer:

```text
I used core RAG and dense retrieval ideas, but shaped the system for telecom support: exact policy IDs, acronyms, regions, products, access levels, escalation paths, citations, and fallback behavior matter more than open-ended chat. The next research-aligned upgrades are stronger embeddings, a real reranker, RAGAS-style faithfulness metrics, and feedback-driven regression evaluation.
```

## Data Sources And 1M Claim

Current demo data:

- `data/raw/*.md`: small sample telecom SOP/runbook/policy documents.
- User-uploaded ZIPs through `/upload` or `POST /ingest/upload`.
- Supported upload file types: `.md`, `.txt`, `.csv`, `.pdf`.

Scale benchmark data:

- 1M benchmark uses MS MARCO passages and judged queries.
- It measures Qdrant indexing/query speed and rough retrieval quality.
- It does not prove production answer quality on telecom data.

Safe wording:

```text
The built-in demo uses sample telecom documents. Users can upload their own ZIP of supported files, which are parsed, chunked, embedded, and indexed for RAG. The 1M-scale benchmark uses MS MARCO passages in Qdrant to measure vector indexing throughput and query latency, not private telecom data.
```

## Enterprise Gap Checklist

### 1. Auth Per Tenant / User

What it means:

- Each customer/company has its own users.
- Each request knows `tenant_id`, `user_id`, and role.
- Auth should use Cognito/OIDC/JWT in AWS, not one shared API key.

Why it matters:

- Prevents one customer from seeing another customer's docs.
- Enables audit logs and per-user permissions.

Current repo:

- API-key auth exists.
- Demo request identity exists through `X-Tenant-ID`, `X-User-ID`, and `X-User-Roles`.
- No validated OIDC/JWT tenant identity yet.

Build path:

1. Add Cognito user pool or OIDC provider.
2. Validate JWT in middleware.
3. Extract `tenant_id`, `user_id`, `roles`.
4. Replace demo headers with verified claims in logs and retrieval filters.
5. Reject missing/invalid identity in production.

Edge cases:

- Expired token.
- User removed from tenant but token still valid.
- Admin role asking across tenants.
- Service-to-service ingestion token.
- Local demo mode without auth.

Interview answer:

```text
API key and demo identity headers are fine for prototypes, but real enterprise needs per-user identity. I would use Cognito/OIDC, validate JWTs in middleware, derive tenant and role claims, and pass verified claims into retrieval filtering and audit logs.
```

### 2. Document ACL Filtering Before Retrieval

What it means:

- Access control happens before or inside vector/keyword search.
- User sees only chunks they are allowed to see.

Why it matters:

- Filtering after retrieving top-k can leak restricted snippets.
- Filtering after search can also hurt recall because allowed docs may never enter top-k.

Current repo:

- Metadata includes `access_level`, `tenant_id`, `allowed_roles`, and `allowed_users`.
- Request filters exist.
- ACLs are enforced inside local vector retrieval, BM25/keyword retrieval, and Qdrant payload filters.
- Public docs without ACL metadata remain visible for demos.

Build path:

1. Replace header-supplied identity with verified OIDC/JWT claims.
2. Add source-of-truth ACL sync from document management systems.
3. Add `source_uri`, document `version`, delete/expiry handling, and reindex jobs.
4. Add Qdrant payload indexes for high-cardinality tenant/user filters.
5. Keep tests proving restricted chunks never return.

Edge cases:

- Public docs plus private docs.
- User role changes after indexing.
- Document deleted but old chunks remain.
- Filter mismatch between Qdrant and BM25.
- Top-k empty because ACL too strict.

Interview answer:

```text
ACLs must be enforced before retrieval, not after answer generation. This prototype stores tenant, user, and role metadata on chunks and applies it in local vector, BM25, and Qdrant retrieval paths. Production still needs verified identity and source-of-truth ACL sync.
```

### 3. Feedback Loop

What it means:

- Users rate answers and reviewers label failures.
- Bad cases become golden eval rows.
- Metrics prove improvement after prompt/retrieval changes.

Why it matters:

- RAG quality improves from real failure cases.
- Gives measurable evidence beyond subjective demos.

Current repo:

- `/feedback` endpoint exists.
- Feedback is stored as JSONL at `data/feedback/feedback.jsonl`.
- Evaluation exists.
- No reviewer dashboard or promote-to-golden command yet.

Build path:

1. Capture `question`, `answer`, `sources`, `rating`, `reason`, `comment`, `expected_doc_id`, and `corrected_answer`.
2. Add tenant/user fields when auth identity exists.
3. Add reviewer dashboard for low-rated answers.
4. Add command to promote feedback into `data/golden_questions.csv`.
5. Run eval before/after each retrieval or prompt change.

Edge cases:

- User downvotes correct answer because policy is unpopular.
- Feedback contains PII.
- Multiple reviewers disagree.
- Feedback spam or abuse.
- Golden set grows biased toward recent incidents.

Interview answer:

```text
I would treat feedback as eval data, not live model training. Low-rated answers are reviewed, labeled by failure type, promoted into golden questions when useful, and used to prevent regressions.
```

### 4. Prompt Lab

What it means:

- Admin/reviewer can test custom prompts against fixed questions and uploaded docs.
- Baseline prompt and custom prompt are compared using same eval set.

Why it matters:

- Prompt changes can improve format but damage faithfulness.
- Users need safe customization without removing grounding rules.

Current repo:

- Locked grounding guardrail exists.
- `/prompt-lab/run` compares baseline vs candidate style/template prompt on golden questions.
- Results are stored under `data/processed/prompt_lab/`.
- No UI, prompt registry, or publish gate yet.

Build path:

1. Keep locked guardrail prompt separate from editable style/template prompt.
2. Add prompt config model with name/version/status.
3. Run baseline vs candidate on golden questions.
4. Report citations, fallback rate, hallucination-risk proxy, latency, and cost.
5. Allow publishing only after metrics pass thresholds.

Edge cases:

- User prompt says "ignore citations".
- User prompt asks for unsupported facts.
- Prompt works for 5 examples but fails on edge cases.
- Prompt increases token cost too much.
- Prompt leaks internal instructions.

Interview answer:

```text
I let users customize answer style/template, but keep grounding rules locked. Prompt Lab compares candidate prompts against golden questions. The next step is to block publishing if citation, fallback, or faithfulness metrics regress.
```

### 4a. LLM Firewall / Sensitive Data Guardrails

What it means:

- App checks user prompts before retrieval/LLM call.
- App redacts sensitive data before sending context to an LLM.
- App scans generated answers and citations before returning them.
- Users can provide their own LLM API key per request instead of using the demo operator key.

Why it matters:

- Prevents obvious jailbreak/model-theft attempts from reaching the model.
- Reduces accidental PII/PCI/secret leakage.
- Controls token abuse and cost spikes.
- Separates platform demo from customer LLM billing/key ownership.

Current repo:

- Lightweight LLM firewall exists in `app/security/llm_firewall.py`.
- `/ask` blocks jailbreak/model-theft/PHI-exfil prompts with HTTP 400.
- `/ask` redacts PII/PCI/secrets before retrieval and again before response.
- `/ask` returns a guardrail report.
- `X-OpenAI-API-Key` can supply a per-request user OpenAI key when `ALLOW_USER_OPENAI_API_KEY=true`.
- Token budgets exist for question, context, and answer sizes.
- `/ask` writes sanitized audit rows with question hashes, not raw questions.
- `GET /guardrails/metrics` reports block/redaction/category/fallback/latency aggregates.

Limits:

- Regex redaction is not full DLP.
- It does not prove HIPAA, PCI, or GDPR compliance.
- It does not replace validated tenant identity, KMS, immutable audit retention, or provider-side safety controls.
- Jailbreak detection is a first-pass blocklist, not perfect adversarial defense.

Build path:

1. Replace demo identity headers with validated JWT/OIDC identity.
2. Move BYOK from raw request header to encrypted tenant key vault with KMS.
3. Add provider-side moderation/DLP or enterprise data-loss prevention.
4. Move local audit logs to immutable managed storage and SIEM.
5. Track guardrail block/redaction rates in hosted monitoring.
6. Add CI tests for known jailbreak and exfiltration prompts.

Interview answer:

```text
I added a lightweight LLM firewall: prompt-injection/model-theft blocks, PII/PCI/secret redaction, token budgets, response scanning, per-request BYO OpenAI keys, sanitized audit logs, and guardrail metrics. I would not call it compliance-grade yet; production needs DLP, KMS-backed BYOK storage, verified identity, immutable audit retention, and provider-side controls.
```

### 4b. Audit Logs / Guardrail Metrics

What it means:

- Each important request event has a durable audit record.
- Guardrail metrics can be inspected without reading raw logs.
- Logs avoid raw prompts, raw secrets, and raw API keys.

Current repo:

- `/ask` appends sanitized JSONL to `data/audit/audit.jsonl`.
- Audit rows include request ID, timestamp, route, tenant/user/roles, question hash, action, guardrail categories, retrieved doc IDs, latency, insufficient-information flag, and confidence.
- `GET /guardrails/metrics` aggregates local audit JSONL.

Limits:

- JSONL is local append-only storage, not immutable WORM retention.
- No hosted SIEM, tracing, alerting, or per-tenant reporting yet.
- Local file writes are not enough for regulated evidence collection.

Build path:

1. Stream audit events to CloudWatch, S3 Object Lock, OpenSearch, or a SIEM.
2. Add retention policies, encryption, access controls, and tamper-evidence.
3. Add dashboards and alerts for block/redaction spikes.
4. Add per-tenant audit export with admin authorization.

Interview answer:

```text
This is app-layer auditability, not compliance proof. It writes sanitized request records and aggregates guardrail metrics locally. Production should send the same event shape to immutable managed storage and SIEM monitoring.
```

### 5. Async S3 / SQS / ECS Ingestion

What it means:

- Large uploads do not stream through FastAPI.
- Upload goes to S3, event goes to SQS, worker processes documents asynchronously.

Why it matters:

- 1M docs cannot be ingested through one HTTP request.
- Workers can retry, scale, and report progress.

Current repo:

- Small ZIP upload exists.
- AWS shape documented.
- No S3/SQS worker yet.

Build path:

1. Browser requests S3 presigned multipart upload.
2. User uploads ZIP/files directly to S3.
3. S3 event sends message to SQS.
4. ECS/Fargate worker reads SQS message.
5. Worker parses, chunks, embeds, and batch-upserts to Qdrant.
6. Status table tracks progress/errors.
7. UI shows docs/sec, chunks/sec, failures, ETA.

Edge cases:

- Duplicate S3 events.
- Partial multipart upload.
- Poison SQS message.
- Worker killed mid-ingestion.
- Zip bomb or malicious file path.
- Re-indexing same document version.

Interview answer:

```text
The `/upload` button is for small demos. For enterprise scale I would use S3 multipart upload, SQS-backed workers, idempotent document versions, batched embedding, and Qdrant batch upserts with progress tracking.
```

### 6. Stronger Embeddings By Default

What it means:

- Use semantic embedding model good enough for production retrieval.
- Keep hashing only for cheap deterministic demos/tests.

Why it matters:

- Current 1M recall is low because hashing embeddings are weak.
- Better embeddings improve semantic recall.

Current repo:

- Hashing embeddings default.
- Sentence-transformers option exists.

Build path:

1. Use `BAAI/bge-small-en-v1.5` or stronger model locally.
2. Consider managed embeddings for AWS production.
3. Re-index all chunks after embedding dimension/model change.
4. Track recall, MRR, precision@k, p95 latency, and cost.
5. Store embedding model/version in index metadata.

Edge cases:

- Vector dimension mismatch.
- Model upgrade changes retrieval behavior.
- Domain acronyms still need BM25.
- Multilingual docs need multilingual embeddings.
- Cost spikes on re-index.

Interview answer:

```text
Hashing embeddings make demos deterministic, but they are not enough for high-quality production retrieval. I would benchmark BGE or managed embeddings against the golden set, track quality/cost/latency, and version the embedding model in the index.
```

### 7. Real Reranker Model

What it means:

- Cross-encoder or reranking API rescores top candidates with query + chunk together.

Why it matters:

- Initial retrieval maximizes recall.
- Reranker improves precision and answer context quality.

Current repo:

- Lexical fallback reranker exists.
- No cross-encoder reranker active by default.

Build path:

1. Retrieve 50-200 candidates.
2. Rerank with cross-encoder or hosted reranker.
3. Keep top 4-8 chunks for answer context.
4. Cache rerank results for repeated queries.
5. Track precision@1, MRR, latency, and cost.

Edge cases:

- Reranker too slow.
- Long chunks exceed reranker limits.
- Reranker overfits lexical overlap.
- Bad initial retrieval means reranker cannot recover.
- Different reranker behavior by language/domain.

Interview answer:

```text
I would use hybrid search for recall and a cross-encoder reranker for precision. Reranking adds latency, so I would measure precision@1 and p95 latency together before enabling it broadly.
```

### 8. RAGAS / Faithfulness Eval

What it means:

- Evaluate whether answer is grounded in provided context, not only whether retrieval found expected docs.

Why it matters:

- Correct document retrieval does not guarantee faithful answer.
- Hallucinations can happen even with good citations.

Current repo:

- Retrieval metrics exist.
- Citation/hallucination proxies exist.
- No RAGAS-style answer eval yet.

Build path:

1. Build eval dataset: question, expected answer, expected source doc/chunk.
2. Generate answers with candidate system.
3. Run faithfulness, answer relevancy, context precision/recall metrics.
4. Fail CI if faithfulness or citation metrics regress.
5. Manually review low-confidence cases.

Edge cases:

- LLM judge inconsistency.
- Evaluation cost.
- Answer correct but phrased differently.
- Multiple valid source docs.
- Gold answer outdated after policy update.

Interview answer:

```text
Retrieval metrics tell me whether the right context was found. Faithfulness eval tells me whether the generated answer stayed inside that context. I would use both because either one alone can hide failures.
```

### 9. Audit Logs

What it means:

- Every sensitive action and answer request has traceable logs.

Why it matters:

- Enterprise users need incident review, compliance, and debugging.

Current repo:

- Structured request logs exist.
- `/ask` writes sanitized audit JSONL to `data/audit/audit.jsonl`.
- Audit rows include question hashes, guardrail categories, retrieved doc IDs, confidence, fallback flag, and latency.
- `GET /guardrails/metrics` aggregates local audit records.

Build path:

1. Add ingestion audit events for uploaded object, document IDs, version, user, and status.
2. Send logs to CloudWatch/S3 Object Lock/OpenSearch/SIEM.
3. Add retention, encryption, tamper-evidence, and access controls.
4. Keep raw question/answer storage off by default because PII risk exists.
5. Add per-tenant audit export with admin authorization.

Edge cases:

- Logs accidentally store PII.
- Need right retention period.
- User asks for deletion.
- Debug logs expose secrets.
- Cross-region compliance.

Interview answer:

```text
I log enough for traceability without dumping sensitive content by default: request id, tenant id, user id, source doc ids, question hash, guardrail categories, confidence, fallback flag, and latency. Production should move those events to immutable managed storage and SIEM.
```

### 10. Source Provenance UI

What it means:

- User can see exactly which documents/chunks supported answer.
- UI shows source title, metadata, excerpt, upload source, version, and access level.

Why it matters:

- Enterprise users trust answers only when they can inspect sources.
- Debugging bad answers requires seeing retrieved context.

Current repo:

- API response includes source citations.
- No polished source UI yet.

Build path:

1. Build answer UI with source side panel.
2. Show chunk excerpts and metadata.
3. Add source document link or download where allowed.
4. Add "why this source?" retrieval score details for reviewers.
5. Add missing/incorrect citation feedback button.

Edge cases:

- Source document deleted after answer.
- User can see answer but not full source doc.
- Citation excerpt too short to prove answer.
- Same policy exists in old and new versions.
- Uploaded filename exposes sensitive info.

Interview answer:

```text
Source provenance is part of the product, not a debug detail. I would show cited chunks, document version, metadata, and source links so users can verify the answer and reviewers can diagnose retrieval failures.
```

### 11. Monitoring

What it means:

- Track live quality, latency, failures, and cost.

Why it matters:

- RAG can degrade silently when docs, prompts, embeddings, or traffic change.

Current repo:

- Basic latency in response.
- Structured logs.
- No CloudWatch metric dashboards/alerts yet.

Build path:

1. Emit metrics: p50/p95/p99 latency, fallback rate, empty retrieval rate, bad feedback rate, retrieval errors, Qdrant errors.
2. Track ingestion metrics: docs/sec, chunks/sec, failed docs, embedding latency, upsert latency.
3. Track cost: tokens, embedding calls, reranker calls.
4. Add CloudWatch dashboards and alarms.
5. Alert on high fallback rate, high p95, high 5xx, ingestion failure spikes.

Edge cases:

- Traffic spike hides quality regression.
- Low fallback rate can mean overconfident hallucination.
- P95 okay but p99 terrible.
- Tenant-specific failures hidden by global average.
- Metrics cardinality explosion from per-user labels.

Interview answer:

```text
I would monitor p95 latency, fallback rate, empty retrieval rate, bad-feedback rate, Qdrant errors, ingestion failures, and cost. Quality metrics matter as much as uptime because RAG can serve fast wrong answers.
```

### 12. Regression Eval In CI

What it means:

- Pull requests must pass retrieval and answer-quality eval on golden questions.

Why it matters:

- Prompt, chunking, retrieval, and embedding changes can silently break quality.

Current repo:

- CI smoke exists.
- Retrieval eval command exists.
- Need stricter thresholds and answer eval.

Build path:

1. Keep a small CI golden set committed.
2. Run ingestion and retrieval eval in CI.
3. Fail if hit rate, precision@1, MRR, fallback rate, or faithfulness regress beyond threshold.
4. Store eval JSON artifact.
5. Run larger eval nightly.

Edge cases:

- Tiny eval set overfits.
- Non-deterministic LLM outputs.
- Golden questions outdated.
- CI cost too high.
- Threshold too strict blocks useful changes.

Interview answer:

```text
I would treat RAG changes like search-ranking changes: every PR runs a golden eval, stores metrics, and fails if retrieval or faithfulness regress beyond threshold. Larger expensive evals can run nightly.
```

## Build Order

Fastest path to make project more enterprise credible:

1. Source provenance answer UI.
2. Provider-grade DLP and encrypted BYOK vault.
3. Feedback reviewer workflow and promote-to-golden command.
4. Prompt Lab publish gate.
5. OIDC/JWT identity replacing demo ACL headers.
6. Stronger embedding benchmark.
7. Real reranker benchmark.
8. RAGAS/faithfulness eval script.
9. CI thresholds and eval artifacts.
10. S3/SQS/ECS ingestion worker.
11. Immutable audit storage/SIEM dashboards.
12. CloudWatch metrics and alarms.
13. Per-tenant audit export.

Why this order:

- Feedback capture, Prompt Lab API, lightweight LLM firewall, ACL-before-retrieval, audit logs, and guardrail metrics are implemented at app layer; reviewer/publish/DLP workflows are next.
- OIDC identity and source-of-truth ACL sync prevent dangerous security claims.
- Embeddings/reranker/RAGAS make quality claims stronger.
- Async AWS and Cognito are production work, bigger than demo code.

## Rebuild Checklist

Use this when recreating project from scratch:

```text
1. Build ingestion: parse -> clean -> metadata -> chunk.
2. Add embeddings: hashing for tests, BGE/managed embeddings for quality.
3. Store chunks with doc_id, chunk_id, source_path, tenant_id, ACL metadata, version.
4. Add vector search in Qdrant.
5. Add BM25 keyword search.
6. Fuse rankings with RRF.
7. Add reranker.
8. Generate grounded answer with citations/confidence/fallback.
9. Add source provenance response model.
10. Add golden eval for retrieval.
11. Add faithfulness eval for answers.
12. Add feedback capture.
13. Add prompt lab with locked grounding guardrails.
14. Add LLM firewall and sensitive-data redaction.
15. Add auth and ACL enforcement.
16. Add async ingestion for large uploads.
17. Add audit logs and monitoring.
18. Add CI regression gates.
```

## Hard Interview Questions

### "How do you know your RAG is best?"

```text
I would not say it is best. I would say it is measured. I compare retrieval hit rate, precision@1, MRR, faithfulness, fallback rate, p95 latency, and bad-feedback rate across prompt, chunking, embedding, and reranker variants. Best means best on the target business eval set under latency and cost constraints.
```

### "Why not fine-tune?"

```text
For policy/support knowledge, facts change often and must be sourced. RAG is better first because it updates through documents and gives citations. Fine-tuning can help tone, routing, or structured formatting later, but it should not be the primary source of changing policy knowledge.
```

### "What if retrieved docs are wrong?"

```text
The generator should stay grounded but cannot fix a bad corpus. I would use document versioning, owner approval, source freshness metadata, feedback reports, and eval failures to find stale or incorrect documents.
```

### "What if user has no access to correct doc?"

```text
Then the system should return insufficient information rather than leak restricted content. ACL filtering must happen inside retrieval, and logs should show the query had no accessible supporting source.
```

### "What if top result is wrong but answer sounds confident?"

```text
That is why confidence cannot be only vector score. I would combine retrieval score, reranker score, citation support, answer faithfulness checks, and fallback thresholds, then review bad-feedback cases.
```

### "Why hybrid search?"

```text
Telecom support has acronyms, policy IDs, SIM/IMEI/MSISDN terms, and region names. Dense retrieval helps semantic phrasing; BM25 catches exact identifiers. RRF combines both without over-trusting one method.
```

### "What breaks at 1M docs?"

```text
HTTP upload, single-process ingestion, non-idempotent jobs, unfiltered vector search, weak embeddings, storage persistence, retry handling, and observability. Production needs S3 multipart upload, SQS workers, batch embeddings, Qdrant payload filters, status tracking, and p95 monitoring.
```

### "How would users test their own prompt?"

```text
Prompt Lab lets them create a candidate style/template prompt, run it against fixed golden questions on their corpus, and compare against baseline. Publishing should stay blocked until citation, fallback, faithfulness, latency, and cost thresholds pass.
```

### "Do you have guardrails or an LLM firewall?"

```text
Yes, at app layer. I block obvious jailbreak/model-theft prompts, redact PII/PCI/secrets before retrieval and before returning answers, cap token budgets, keep grounding rules locked, enforce ACLs inside retrieval, write sanitized audit logs, and expose guardrail metrics. I would still call it a first layer, not full compliance. Enterprise rollout needs DLP, KMS-backed BYOK, verified tenant identity, immutable audit retention, SIEM monitoring, and provider-side controls.
```

### "Whose API key pays for the LLM?"

```text
For local demos, the server can use OPENAI_API_KEY or the caller can send X-OpenAI-API-Key per request. For real customers, I would use customer-owned keys stored encrypted per tenant, never in request bodies or logs, with rotation, billing limits, and audit trails.
```

### "How would users upload their own data?"

```text
For demos, upload a ZIP through `/upload`. For production, upload directly to S3 using presigned multipart URLs. An SQS-backed worker parses, chunks, embeds, indexes into Qdrant, and updates ingestion status for the UI.
```
