from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, eval_runs
from app.routers.models import router as models_router
from app.routers.datasets import router as datasets_router
from app.routers.baselines_alerts import baselines_router, alerts_router
from app.routers.billing import router as billing_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are created via Alembic migrations (alembic upgrade head),
    # run manually before deploy. We do NOT call init_db() here because
    # it tries to open its own DB connection on every cold start, and
    # any connection issue (e.g. wrong password, DB asleep) crashes the
    # whole app before it can even serve /health.
    yield


app = FastAPI(
    title="EvalForge API",
    description="LLM Evaluation & Red-Teaming Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
# Explicit origins list + regex fallback so any *.vercel.app preview/production
# URL works without needing to update this file every time Vercel changes the URL.
origins = [
    settings.frontend_url,
    "https://evalforge-vedashree-kulkarni-s-projects.vercel.app",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(eval_runs.router)
app.include_router(models_router)
app.include_router(datasets_router)
app.include_router(baselines_router)
app.include_router(alerts_router)
app.include_router(billing_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
async def root():
    return {"message": "EvalForge API — visit /docs for Swagger UI"}
