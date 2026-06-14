from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import auth, eval_runs
from app.routers.models import router as models_router
from app.routers.datasets import router as datasets_router
from app.routers.baselines_alerts import baselines_router, alerts_router
from app.routers.billing import router as billing_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "development":
        await init_db()
    yield


app = FastAPI(
    title="EvalForge API",
    description="LLM Evaluation & Red-Teaming Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "https://evalforge-indol.vercel.app",
        "http://localhost:3000",
    ],
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
