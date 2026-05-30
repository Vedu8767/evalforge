# EvalForge — Complete Getting Started Guide
# From zero to running app — every single step

---

## WHAT YOU'LL HAVE AT THE END
- A running LLM Evaluation SaaS on your machine
- Backend API at: http://localhost:8000
- Frontend at: http://localhost:3000
- API docs at: http://localhost:8000/docs
- Deployed live at: evalforge.vercel.app (after Step 6)

---

## PREREQUISITES — Install these first

### 1. Python 3.12
```bash
# Check if you have it:
python3 --version   # needs to say 3.12.x

# Install on Mac:
brew install python@3.12

# Install on Ubuntu/Debian:
sudo apt update && sudo apt install python3.12 python3.12-venv python3-pip
```

### 2. Node.js 20+
```bash
# Check:
node --version   # needs 20+

# Install: https://nodejs.org → Download LTS
# OR with nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20 && nvm use 20
```

### 3. Docker Desktop
```bash
# Download: https://www.docker.com/products/docker-desktop
# After install, check:
docker --version
docker-compose --version
```

### 4. Git
```bash
git --version
# Install: https://git-scm.com
```

### 5. OpenAI API Key
- Go to: https://platform.openai.com/api-keys
- Create new key → copy it (you'll need it in Step 3)
- Free tier gives $5 credit — enough for 500+ evals

---

## STEP 1 — Get the project

### Option A: Download (easiest)
Download the zip file from Claude → extract to a folder called `evalforge`

### Option B: Clone from GitHub (after you push)
```bash
git clone https://github.com/YOUR_USERNAME/evalforge
cd evalforge
```

After extracting/cloning, you should see:
```
evalforge/
├── backend/
├── frontend/
├── docker-compose.yml
├── README.md
└── DEPLOYMENT.md
```

---

## STEP 2 — Start the Database and Redis

```bash
# From the evalforge/ root folder:
docker-compose up -d
```

Wait 10 seconds, then verify:
```bash
docker ps
```

You should see TWO containers running:
- `evalforge_postgres` — the database
- `evalforge_redis` — the job queue

If you see them, Step 2 is done ✅

**Troubleshooting:**
- "Port 5432 already in use" → Stop any local PostgreSQL: `sudo service postgresql stop`
- "Port 6379 already in use" → Stop local Redis: `sudo service redis stop`

---

## STEP 3 — Setup the Backend

```bash
# Move into backend folder
cd backend

# Create a Python virtual environment
python3 -m venv venv

# Activate it (run this every time you open a new terminal)
source venv/bin/activate          # Mac/Linux
venv\Scripts\activate             # Windows

# Your terminal prompt should now show (venv)
```

### Install dependencies
```bash
pip install -r requirements.txt
```
This takes 2-3 minutes. You'll see lots of packages installing.

### Configure environment variables
```bash
# Copy the example env file
cp .env.example .env

# Open .env in any text editor and fill in:
nano .env       # or: code .env  or: notepad .env
```

**Minimum required changes in .env:**
```bash
# Change this line — add your real OpenAI key:
OPENAI_API_KEY=sk-your-actual-key-here

# These can stay as-is for local development:
DATABASE_URL=postgresql+asyncpg://evalforge:evalforge_dev@localhost:5432/evalforge
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=change-me-in-production
ENCRYPTION_KEY=change-me-32-bytes-hex-in-prod!!
```

### Run database migrations
```bash
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial, Initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial -> 0002_indexes, Add performance indexes
INFO  [alembic.runtime.migration] Running upgrade 0002_indexes -> 0003_stripe, Add Stripe columns
```

### Seed demo data
```bash
python seed.py
```

Expected output:
```
🌱 Seeding database...
   ✅ Workspace:  Demo Workspace
   ✅ User:       demo@evalforge.dev (password: demo1234)
   ✅ Dataset:    'General Knowledge QA' (10 rows)
   ✅ Dataset:    'Tech Concepts Factual' (5 rows)
   ✅ Model:      GPT-4o-mini (Demo)
   ✅ Alert:      'Low overall score' (overall_score < 70)
✅  Seed complete!
```

### Verify everything is healthy
```bash
python check_db.py
```

All lines should show ✅. If anything shows ❌, fix it before continuing.

---

## STEP 4 — Start the Backend API

**Keep this terminal open — the API runs here.**

```bash
# Make sure you're in backend/ with venv activated
uvicorn app.main:app --reload --port 8000
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test it works:**
Open a new terminal and run:
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok","version":"0.1.0"}
```

Or open: http://localhost:8000/docs — you'll see the full Swagger API docs.

---

## STEP 5 — Start the Celery Worker

**Open a NEW terminal. Keep Step 4 terminal running.**

```bash
# Navigate back to backend/
cd evalforge/backend

# Activate venv again in this new terminal
source venv/bin/activate

# Start Celery worker
celery -A celery_worker worker --loglevel=info
```

Expected output:
```
[config]
.> app:         evalforge:0x...
.> transport:   redis://localhost:6379/0
.> results:     redis://localhost:6379/0
.> concurrency: 8 (prefork)

[tasks]
  . tasks.run_eval

[2025-01-01 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-01-01 10:00:00,000: INFO/MainProcess] mingle: searching for neighbors
[2025-01-01 10:00:00,000: INFO/MainProcess] mingle: all alone
[2025-01-01 10:00:00,000: INFO/MainProcess] celery@hostname ready.
```

When you see "ready" — the worker is running ✅

---

## STEP 6 — Setup the Frontend

**Open another NEW terminal.**

```bash
cd evalforge/frontend

# Install Node packages
npm install
```
This takes 1-2 minutes.

### Configure frontend environment
```bash
cp .env.local.example .env.local
```

Open `.env.local` and set:
```bash
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=any-random-string-at-least-32-chars-long

# For Google login (optional — can skip for now):
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

NEXT_PUBLIC_API_URL=http://localhost:8000
```

**To generate a random NEXTAUTH_SECRET:**
```bash
openssl rand -base64 32
# Copy the output and paste it as NEXTAUTH_SECRET
```

### Start the frontend
```bash
npm run dev
```

Expected output:
```
▲ Next.js 14.2.3
- Local:        http://localhost:3000
- Environments: .env.local

✓ Ready in 2.1s
```

---

## STEP 7 — Use the App

Open your browser: **http://localhost:3000**

You'll be redirected to the login page.

### Login with demo account:
- Email: `demo@evalforge.dev`
- Password: `demo1234`

### Your first eval run (5 minutes):

**Step 1 — Add your OpenAI key to the model:**
1. Click "Models" in sidebar
2. You'll see "GPT-4o-mini (Demo)" — click the 3 dots → Edit
3. Update the API key with your real OpenAI key
4. Click "Test" — should show ✅ Connected

**Step 2 — Create an eval run:**
1. Click "New Eval Run" (top right)
2. Step 1: Select "GPT-4o-mini (Demo)"
3. Step 2: Select "General Knowledge QA" (10 rows)
4. Step 3: Check "Factual Accuracy" + "Hallucination Detection"
5. Step 4: Click "Launch Eval Run"

**Step 3 — Watch it run:**
You'll be taken to the live run page. Watch results stream in real-time. Each row shows:
- The model's actual output
- Whether hallucination was detected
- Factual accuracy score
- Response latency

When complete, you'll see overall scores on the dashboard.

---

## TERMINAL LAYOUT (keep all 3 running)

```
Terminal 1 (API):      cd backend && uvicorn app.main:app --reload --port 8000
Terminal 2 (Worker):   cd backend && celery -A celery_worker worker --loglevel=info
Terminal 3 (Frontend): cd frontend && npm run dev
```

---

## STEP 8 — Run Tests

```bash
# In backend/ with venv activated:
pytest tests/ -v

# With coverage:
pytest tests/ -v --cov=app --cov-report=term-missing
```

Expected: All tests passing ✅

---

## STEP 9 — Push to GitHub

```bash
# From evalforge/ root:
git init
git add .
git commit -m "feat: EvalForge — LLM Evaluation & Red-Teaming Platform

- FastAPI backend with async eval pipeline
- Hallucination detection (self-consistency + LLM-as-judge)
- Jailbreak resistance testing (10 probes, 5 categories)
- Factual accuracy evaluation
- Real-time SSE result streaming
- Multi-tenant SaaS with Stripe billing
- Next.js 14 dashboard
- PostgreSQL + pgvector + Redis + Celery"

# Create repo on GitHub: github.com/new
# Then:
git remote add origin https://github.com/YOUR_USERNAME/evalforge
git push -u origin main
```

GitHub Actions will automatically run tests on push.

---

## STEP 10 — Deploy to Production (FREE)

See `DEPLOYMENT.md` for the full guide. Summary:

| What | Service | Time |
|------|---------|------|
| Database | Supabase (free) | 5 min |
| Redis | Upstash (free) | 2 min |
| API + Worker | Railway (free tier) | 10 min |
| Frontend | Vercel (free) | 5 min |
| **Total** | **$0/month** | **22 min** |

---

## COMMON ERRORS & FIXES

### "ModuleNotFoundError"
```bash
# Forgot to activate venv:
source venv/bin/activate
```

### "Connection refused" on port 5432
```bash
# Docker not running or postgres container stopped:
docker-compose up -d
docker ps   # verify containers are running
```

### "alembic: command not found"
```bash
# Not in venv or venv not activated:
source venv/bin/activate
which alembic   # should show path inside venv
```

### "OPENAI_API_KEY not set" errors in eval runs
```bash
# Edit backend/.env and add your key:
OPENAI_API_KEY=sk-your-key-here
# Then restart the API and worker
```

### Frontend shows "Network Error"
```bash
# API not running. Start it:
cd backend && uvicorn app.main:app --reload --port 8000
# Also check NEXT_PUBLIC_API_URL in frontend/.env.local
```

### Celery worker shows "Cannot connect to redis"
```bash
# Redis container not running:
docker-compose up -d
# Verify: docker ps | grep redis
```

---

## PROJECT STRUCTURE EXPLAINED

```
evalforge/
│
├── backend/                     ← FastAPI Python backend
│   ├── app/
│   │   ├── main.py              ← App entry point, all routers registered
│   │   ├── config.py            ← All env vars (reads from .env)
│   │   ├── db.py                ← PostgreSQL async connection
│   │   ├── models/orm.py        ← All 10 database table definitions
│   │   ├── schemas/schemas.py   ← Request/response validation
│   │   ├── routers/             ← API endpoints
│   │   │   ├── auth.py          ← Register, login, /me
│   │   │   ├── eval_runs.py     ← Create/list/stream eval runs
│   │   │   ├── models.py        ← Register LLM endpoints
│   │   │   ├── datasets.py      ← Upload datasets (CSV/JSONL)
│   │   │   ├── billing.py       ← Stripe checkout + webhooks
│   │   │   └── baselines_alerts.py
│   │   ├── services/
│   │   │   ├── auth.py          ← JWT + AES-256 API key encryption
│   │   │   ├── llm_client.py    ← Calls OpenAI/Anthropic/custom APIs
│   │   │   ├── embeddings.py    ← OpenAI embeddings + cosine similarity
│   │   │   └── eval_engine/
│   │   │       ├── hallucination.py  ← Self-consistency + LLM judge
│   │   │       ├── jailbreak.py      ← 10 adversarial probes
│   │   │       ├── factual.py        ← LLM-as-judge scoring
│   │   │       └── regression.py     ← Diff vs baseline
│   │   └── tasks/eval_tasks.py  ← Celery async job orchestrator
│   │
│   ├── alembic/versions/        ← Database migrations (run in order)
│   │   ├── 0001_initial.py      ← Creates all 10 tables
│   │   ├── 0002_indexes.py      ← Performance indexes + HNSW vector index
│   │   └── 0003_stripe.py       ← Plan constraint + usage view
│   │
│   ├── tests/test_api.py        ← 20+ API tests
│   ├── seed.py                  ← Demo data (run once after migrations)
│   ├── check_db.py              ← Verify everything before starting
│   ├── manage.py                ← DB management CLI
│   ├── requirements.txt         ← All Python packages
│   └── .env.example             ← Copy to .env and fill in values
│
├── frontend/                    ← Next.js 14 React frontend
│   └── src/app/
│       ├── dashboard/           ← Score cards + trend chart
│       ├── eval-runs/           ← List, new wizard, live detail
│       ├── datasets/            ← Upload + manage datasets
│       ├── models/              ← Register LLM endpoints
│       ├── settings/            ← Alert rules + team + billing
│       └── billing/             ← Stripe plan upgrade page
│
├── .github/workflows/           ← CI/CD (auto-runs on push)
│   ├── deploy.yml               ← Full pipeline (test + deploy)
│   ├── pr.yml                   ← PR validation
│   └── nightly.yml              ← Daily health check
│
└── docker-compose.yml           ← Local PostgreSQL + Redis
```

---

## WHAT TO PUT ON YOUR RESUME

**Project Title:**
EvalForge — LLM Evaluation & Red-Teaming Platform | github.com/you/evalforge

**Bullet points (pick 4):**
- Built production SaaS for automated LLM evaluation with hallucination detection (self-consistency sampling + LLM-as-judge), jailbreak resistance testing across 5 attack categories, and regression tracking
- Designed hallucination pipeline using N=3 self-consistency sampling with cosine similarity on text-embedding-3-small vectors stored via pgvector, achieving structured LLM verdict extraction
- Implemented async eval job orchestration with Celery + Redis supporting configurable concurrency (1–20 workers); real-time result streaming to frontend via Server-Sent Events (SSE)
- Built multi-tenant SaaS with JWT auth, AES-256 API key encryption, Stripe subscription billing (free/pro/team), and plan enforcement middleware
- Deployed on Railway (FastAPI + Celery) + Vercel (Next.js 14) with 8-job GitHub Actions CI/CD pipeline including migration round-trip verification and Slack failure alerts

**Skills shown:**
FastAPI · Next.js · PostgreSQL · pgvector · Celery · Redis · Stripe · Docker · GitHub Actions · OpenAI API · LLM evaluation · RAG · System design

---

## HOW TO EXPLAIN IN INTERVIEWS

**30-second version:**
"I built EvalForge — a SaaS that lets AI teams automatically test their LLMs before shipping. It detects hallucinations using self-consistency sampling, runs jailbreak probes across five attack categories, and tracks regression against baseline versions. The tech stack is FastAPI + Celery for async eval jobs, PostgreSQL with pgvector for embedding storage, Next.js for the dashboard, and Stripe for billing. It's deployed on Railway and Vercel."

**When asked about the hardest part:**
"The trickiest part was hallucination detection without ground truth. When you don't have a known correct answer, how do you know if the model is making things up? I implemented self-consistency — run the same prompt three times, embed each response, compute pairwise cosine similarity. Low similarity means the model gives different answers each time, which signals hallucination risk. I layer an LLM-as-judge on top for a structured verdict. The combination gives much better signal than either alone."

**When asked about system design:**
"The eval pipeline is async — the API accepts a run request, writes it to the DB as 'queued', and immediately enqueues a Celery task. The API returns the run ID and the frontend polls or streams via SSE. The Celery worker processes rows with a configurable semaphore for concurrency, runs all eval checks in parallel with asyncio.gather, streams results to the DB row by row, then computes aggregate scores. This means a 500-row dataset doesn't block the API at all."
