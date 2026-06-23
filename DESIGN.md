# EvalForge — System Design Document

## Problem Statement

LLM teams shipping AI-powered products have no systematic way to test whether their models are hallucinating, vulnerable to jailbreaks, or regressing between versions. Manual testing doesn't scale. This is the same problem Google, Anthropic, and OpenAI solve internally — EvalForge makes it accessible to any team.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Client (Browser)                      │
│              Next.js 14 — evalforge.vercel.app           │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS (REST + SSE)
┌──────────────────────▼──────────────────────────────────┐
│                  API Layer (Render)                      │
│              FastAPI — async, uvicorn                    │
│                                                          │
│  /auth/*        JWT auth + bcrypt password hashing       │
│  /eval-runs/*   Eval orchestration + SSE streaming       │
│  /model-endpoints/* AES-256 encrypted API key storage   │
│  /datasets/*    CSV ingestion + row management           │
└──────┬───────────────────────────┬───────────────────────┘
       │                           │
       │ SQLAlchemy async          │ Celery task dispatch
┌──────▼──────────┐    ┌──────────▼────────────────────────┐
│   Supabase      │    │         Upstash Redis              │
│   PostgreSQL    │    │    Task queue + result backend     │
│   + pgvector    │    └──────────┬────────────────────────┘
│                 │               │
│  10 tables:     │    ┌──────────▼────────────────────────┐
│  users          │    │      Celery Worker (same Render    │
│  workspaces     │    │      instance, background thread)  │
│  model_endpoints│    │                                    │
│  datasets       │    │  1. Load dataset rows from DB      │
│  dataset_rows   │◄───│  2. Call LLM via httpx             │
│  eval_runs      │    │  3. Run eval checks (factual,      │
│  eval_results   │    │     hallucination, jailbreak)      │
│  baselines      │    │  4. Save results row by row        │
│  alert_rules    │    │  5. Compute aggregate scores       │
│  workspace_     │    └───────────────────────────────────┘
│  members        │
└─────────────────┘
```

---

## Key Design Decisions

### 1. Hallucination Detection via Self-Consistency Sampling

**Problem:** How do you detect hallucination without ground truth labels?

**Solution:** Self-consistency sampling — run the same prompt N times (N=3), embed each response using text embeddings, compute pairwise cosine similarity. Low similarity = model gives inconsistent answers = hallucination signal.

```python
responses = await call_llm_n_times(prompt, endpoint, n=3)
embeddings = await embed_texts([r.content for r in responses])
consistency_score = average_pairwise_similarity(embeddings)
hallucination_risk = consistency_score < 0.82
```

**Why this approach:**
- Works without labeled data (unsupervised)
- Scales to any domain
- Combines well with LLM-as-judge for a layered signal

**Tradeoffs:**
- 3x API cost per hallucination check
- Doesn't catch consistent hallucinations (model confidently wrong every time)
- Threshold (0.82) is empirical, needs calibration per domain

---

### 2. LLM-as-Judge for Factual Scoring

**Problem:** Traditional NLP metrics (BLEU, ROUGE) don't capture semantic correctness.

**Solution:** Use the same LLM as a judge — prompt it with the question, expected answer, and actual answer, ask it to return a structured JSON score.

**Tradeoffs:**
- Judge LLM can be biased toward verbose or confident-sounding answers
- Self-evaluation (same model judging itself) has known biases
- Mitigated by using a separate judge prompt with explicit rubric

**Production improvement:** Use a stronger judge model than the model being evaluated (e.g., GPT-4 judging GPT-3.5 outputs).

---

### 3. Async Job Architecture

**Problem:** LLM eval on 100+ rows can take minutes. Blocking HTTP requests would time out.

**Solution:** Accept → Queue → Stream pattern:

```
POST /eval-runs          # Returns immediately with run_id
     ↓
Celery task enqueued     # Processes in background
     ↓
GET /eval-runs/{id}/stream  # SSE stream: frontend polls progress
     ↓
Celery commits each row  # DB updated incrementally
```

**Why Celery + Redis over alternatives:**
- FastAPI background tasks: no retry, no distributed workers
- AWS SQS/Lambda: overkill for current scale, vendor lock-in
- Celery: battle-tested, retry logic, monitoring via Flower

---

### 4. Multi-tenant Data Isolation

Every query filters by `workspace_id` extracted from the JWT:

```python
result = await db.execute(
    select(ModelEndpoint)
    .where(ModelEndpoint.workspace_id == UUID(workspace_id))
)
```

**Limitation:** Row-level security not enforced at DB level (only at application layer). Production improvement: Supabase RLS policies for defense in depth.

---

### 5. API Key Encryption

LLM provider API keys are AES-256 encrypted (via Fernet) before storage:

```python
key = sha256(ENCRYPTION_KEY).digest()  # 32-byte key
fernet = Fernet(base64.urlsafe_b64encode(key))
encrypted = fernet.encrypt(api_key.encode())
```

**Tradeoffs:**
- Keys are decryptable (symmetric encryption) — needed to call APIs
- If ENCRYPTION_KEY is compromised, all keys are exposed
- Production: use AWS KMS or HashiCorp Vault for key management

---

## Scalability Analysis

**Current bottlenecks at scale:**

| Bottleneck | At what scale | Solution |
|-----------|---------------|----------|
| Single Celery worker | >50 concurrent evals | Horizontal worker scaling |
| Supabase free tier | >500MB data | Migrate to dedicated Postgres |
| No connection pooling | >100 concurrent users | PgBouncer |
| LLM API rate limits | >100 rows/min | Per-provider rate limiting |
| pgvector HNSW index | >1M embeddings | Tune m and ef_construction params |

**How to scale to 1M eval runs/day:**
1. Separate API and worker services (already architected for this)
2. Horizontal Celery workers with `--concurrency=10`
3. Redis Cluster for high-throughput task queue
4. Read replicas for eval result queries
5. Streaming results to S3 for large datasets (>10k rows)

---

## Security Considerations

| Risk | Mitigation |
|------|-----------|
| SQL injection | SQLAlchemy ORM with parameterized queries |
| JWT forgery | HS256 with 64-char secret, short expiry |
| API key leakage | AES-256 encryption at rest, masked in UI |
| CORS attacks | Explicit origin allowlist + regex |
| Prompt injection in evals | Sandboxed judge prompts with strict JSON output |

---

## What I'd do differently in production

1. **Replace self-signed bcrypt with Argon2** — more secure, actively maintained
2. **Add OpenTelemetry tracing** — trace each eval row end to end
3. **Implement circuit breakers** — stop hammering failing LLM APIs
4. **Add eval run cancellation** — revoke Celery task by ID
5. **Build a comparison view** — side-by-side diff of two eval runs
6. **Use pgvector HNSW index** — for sub-millisecond similarity search at scale
7. **Add webhook support** — notify CI/CD pipelines when eval completes

---

## Interview Talking Points

**"How does hallucination detection work?"**
Self-consistency sampling — run the prompt N times, embed each response, measure cosine similarity of the embedding vectors. Below 0.82 threshold signals inconsistency, which correlates with hallucination. Layer LLM-as-judge on top for a structured verdict.

**"How does the async pipeline work?"**
API accepts request → writes 'queued' to DB → enqueues Celery task → returns run_id immediately. Worker picks up task → processes rows sequentially with configurable concurrency → commits results to DB incrementally → frontend polls via SSE. This way a 500-row eval doesn't block the API at all.

**"How do you prevent one tenant's data from leaking to another?"**
Every DB query filters by workspace_id extracted from the JWT at the application layer. Next step would be Supabase Row Level Security for database-level enforcement — defense in depth.

**"How would you scale this?"**
Horizontal Celery workers are the first lever — each worker processes one eval independently. The architecture already separates API from workers, so scaling workers doesn't require touching the API. For 1M runs/day, add Redis Cluster, read replicas, and stream large result sets to S3 instead of Postgres.
