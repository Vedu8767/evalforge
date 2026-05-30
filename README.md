# EvalForge 🔬

**LLM Evaluation & Red-Teaming SaaS** — Test, benchmark, and red-team any LLM in production.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

---

## What it does

| Feature | Detail |
|---------|--------|
| 🧠 Hallucination Detection | Self-consistency sampling (N=3) + LLM-as-judge |
| 🔴 Jailbreak Testing | 10 adversarial probes across 5 attack categories |
| 📊 Factual Accuracy | LLM judge vs expected output |
| 📉 Regression Testing | Diff any run against a pinned baseline |
| ⚡ Real-time Progress | SSE stream — see results as they come in |
| 💳 Billing | Stripe subscriptions (free / pro / team) |
| 🚨 Alerts | Slack + email when scores drop below threshold |

---

## Tech Stack

- **Frontend**: Next.js 14 + Tailwind CSS + React Query → Vercel
- **Backend**: FastAPI + Celery + Redis → Railway
- **Database**: PostgreSQL + pgvector (Supabase free tier)
- **AI**: OpenAI API (GPT-4o-mini as judge, text-embedding-3-small)

---

## Quick Start (Local)

### Prerequisites
- Docker Desktop (for Postgres + Redis)
- Node.js 20+
- Python 3.12+
- OpenAI API key

### 1. Clone
```bash
git clone https://github.com/yourname/evalforge
cd evalforge
```

### 2. Start infrastructure
```bash
docker-compose up -d
# Starts PostgreSQL (port 5432) + Redis (port 6379)
```

### 3. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY at minimum

# Start API
uvicorn app.main:app --reload --port 8000
```

### 4. Celery Worker (new terminal)
```bash
cd backend
source venv/bin/activate
celery -A celery_worker worker --loglevel=info
```

### 5. Frontend (new terminal)
```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local — set NEXTAUTH_SECRET to any random string

npm run dev
# Open http://localhost:3000
```

### 6. API Docs
Visit http://localhost:8000/docs for interactive Swagger UI.

---

## Project Structure

```
evalforge/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── db.py                # SQLAlchemy async engine
│   │   ├── models/orm.py        # All DB models
│   │   ├── schemas/schemas.py   # Pydantic request/response schemas
│   │   ├── routers/             # API route handlers
│   │   ├── services/
│   │   │   ├── auth.py          # JWT + encryption
│   │   │   ├── llm_client.py    # Unified LLM caller
│   │   │   ├── embeddings.py    # OpenAI embeddings + cosine similarity
│   │   │   └── eval_engine/
│   │   │       ├── hallucination.py
│   │   │       ├── jailbreak.py
│   │   │       └── factual.py
│   │   └── tasks/eval_tasks.py  # Celery async eval pipeline
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/app/
│   │   ├── dashboard/           # Main dashboard
│   │   ├── eval-runs/           # Run list + detail + new wizard
│   │   ├── datasets/            # Dataset management
│   │   └── models/              # Model endpoint management
│   └── src/lib/api.ts           # Typed API client
│
├── docker-compose.yml           # Local dev: Postgres + Redis
└── .github/workflows/deploy.yml # CI/CD
```

---

## Deployment

### Free tier resources used
| Service | Free tier | Usage |
|---------|-----------|-------|
| Railway | $5 credit/mo | FastAPI + Celery worker |
| Vercel | Unlimited hobby | Next.js frontend |
| Supabase | 500MB DB | PostgreSQL + pgvector |
| Redis Cloud | 30MB | Job queue |
| OpenAI | Pay-per-use | Judge calls (~$0.01/eval) |

### Deploy to Railway
```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# From /backend
railway init
railway up --service evalforge-api

# Add second service for Celery worker (same code, different start command)
# Start command: celery -A celery_worker worker --loglevel=info
```

### Deploy frontend to Vercel
```bash
cd frontend
npx vercel --prod
```

---

## Resume Summary

> Built EvalForge — a multi-tenant SaaS for automated LLM evaluation featuring hallucination detection (self-consistency sampling + LLM-as-judge), jailbreak resistance testing across 5 attack categories, and regression testing against pinned baselines. Stack: Next.js + FastAPI + Celery + PostgreSQL + pgvector. Deployed on Railway + Vercel with GitHub Actions CI/CD.

---

## License

MIT — feel free to fork and adapt.
