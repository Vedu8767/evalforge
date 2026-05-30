# EvalForge — Database Setup Guide

Complete reference for setting up, migrating, and managing the database.

---

## Prerequisites

- Docker Desktop running
- Python virtualenv activated (`source venv/bin/activate`)
- `.env` file configured (copy from `.env.example`)

---

## Quick Start (First Time)

```bash
# 1. Start PostgreSQL + Redis
docker-compose up -d

# 2. Activate virtualenv
source venv/bin/activate

# 3. Run all migrations (creates all tables + pgvector extension)
alembic upgrade head

# 4. Seed demo data
python seed.py

# 5. Verify everything is healthy
python check_db.py
```

You should see:
```
✅ PostgreSQL connected
✅ pgvector extension: v0.7.x
✅ All 10 tables exist
✅ 8 performance indexes found (including HNSW vector index)
✅ Alembic version: 0002_indexes
✅ Redis connected
✅ All checks passed — ready to start!
```

---

## Migration Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Apply one migration at a time
alembic upgrade +1

# Roll back one migration
alembic downgrade -1

# Roll back to the very beginning (drops all tables)
alembic downgrade base

# See current migration version
alembic current

# See full migration history
alembic history --verbose

# Preview what SQL will run (without executing)
alembic upgrade head --sql
```

---

## Manage Script (shorthand)

```bash
python manage.py migrate          # Run all pending migrations
python manage.py seed             # Seed demo data
python manage.py status           # Show current version + history
python manage.py reset            # ⚠️  Drop everything, re-migrate, re-seed
python manage.py makemigration "add_column_x"   # Auto-generate migration
```

---

## When You Change a Model

1. Edit `app/models/orm.py`
2. Auto-generate migration:
   ```bash
   alembic revision --autogenerate -m "your description"
   ```
3. **Review** the generated file in `alembic/versions/` — always check it!
4. Apply:
   ```bash
   alembic upgrade head
   ```

### Common gotchas

| Situation | What to do |
|-----------|-----------|
| Added a column | Auto-generate works fine |
| Added a `vector()` column | Write migration manually — Alembic doesn't know pgvector |
| Renamed a column | Auto-generate sees DROP+ADD, not RENAME — fix manually |
| Added an HNSW index | Write manually (it's a raw SQL index) |
| Circular FK (eval_runs ↔ baselines) | Create table first, add FK separately |

---

## Database Schema Quick Reference

```
workspaces          → root multi-tenancy unit
users               → auth
workspace_members   → user ↔ workspace (many-to-many with role)
model_endpoints     → registered LLM endpoints (API key encrypted)
datasets            → collections of test prompts
dataset_rows        → individual prompt/expected pairs
eval_runs           → one full evaluation job
eval_results        → per-row result (embedding stored as vector(1536))
baselines           → pinned eval runs for regression comparison
alert_rules         → metric threshold alerts
```

---

## pgvector Usage

The `output_embedding` column in `eval_results` stores 1536-dim vectors
(OpenAI `text-embedding-3-small`).

```sql
-- Find the 5 most similar past outputs to a given embedding
SELECT id, actual_output, 1 - (output_embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM eval_results
WHERE eval_run_id = 'your-run-id'
ORDER BY output_embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

The HNSW index (created in migration `0002_indexes`) makes this fast at scale.

---

## Free Tier Resources Used

| Service | What | Free limit |
|---------|------|-----------|
| Supabase | PostgreSQL + pgvector | 500MB storage, unlimited rows |
| Railway | Redis | 100MB (more than enough for job queue) |
| Local Docker | Development | Free |

### Supabase Setup (production)

1. Create project at supabase.com (free)
2. Go to Settings → Database → Connection string → URI (use **Session** mode for migrations)
3. Set in `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:[password]@[host]:5432/postgres
   DATABASE_URL_SYNC=postgresql://postgres:[password]@[host]:5432/postgres
   ```
4. pgvector is pre-installed on Supabase — no extra setup needed
5. Run: `alembic upgrade head`

---

## Troubleshooting

**"relation does not exist"**
→ Migrations haven't run. Run: `alembic upgrade head`

**"extension vector does not exist"**
→ Using a plain Postgres image without pgvector.
→ Use `pgvector/pgvector:pg16` in docker-compose (already configured).

**"Can't locate revision"**
→ `alembic/versions/` file has wrong `down_revision`. Check chain.

**Celery tasks not running**
→ Redis not running. Run: `docker-compose up -d`

**"asyncpg: password authentication failed"**
→ Wrong credentials in `DATABASE_URL`. Check `.env`.
