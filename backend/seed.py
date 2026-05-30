"""
Seed Script — populate DB with demo data for local development.

Usage:
    cd backend
    python seed.py

Creates:
    - 1 demo user (demo@evalforge.dev / password: demo1234)
    - 1 workspace
    - 1 sample QA dataset with 10 rows
    - 1 sample jailbreak dataset with 5 rows
    - 1 model endpoint (OpenAI GPT-4o-mini — needs real API key to run evals)
    - 1 alert rule
"""
import asyncio
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select

# ── Path setup ────────────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings
from app.db import Base
from app.models.orm import (
    Workspace, User, WorkspaceMember,
    ModelEndpoint, Dataset, DatasetRow, AlertRule,
)
from app.services.auth import hash_password, encrypt_api_key

# ── Demo data ─────────────────────────────────────────────────────────────────

DEMO_EMAIL = "demo@evalforge.dev"
DEMO_PASSWORD = "demo1234"
DEMO_NAME = "Demo User"

QA_ROWS = [
    ("What is the capital of France?",             "Paris"),
    ("What does CPU stand for?",                    "Central Processing Unit"),
    ("Who wrote Romeo and Juliet?",                 "William Shakespeare"),
    ("What is the speed of light in km/s?",         "Approximately 299,792 km/s"),
    ("What is the largest planet in the solar system?", "Jupiter"),
    ("What year did World War II end?",             "1945"),
    ("What is H2O?",                               "Water — two hydrogen atoms and one oxygen atom"),
    ("Who painted the Mona Lisa?",                  "Leonardo da Vinci"),
    ("What is the powerhouse of the cell?",         "Mitochondria"),
    ("What is the square root of 144?",             "12"),
]

FACTUAL_ROWS = [
    ("Explain what machine learning is in one sentence.",  "Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed."),
    ("What is a REST API?",                               "A REST API is an architectural style for networked applications using HTTP methods to perform CRUD operations on resources."),
    ("What is the difference between SQL and NoSQL?",     "SQL databases are relational and use structured schemas; NoSQL databases are non-relational and flexible in structure."),
    ("What is a Docker container?",                       "A Docker container is a lightweight, standalone executable package that includes everything needed to run an application."),
    ("Explain what an API rate limit is.",                "A rate limit restricts how many API requests a client can make within a given time window to prevent abuse and ensure fair usage."),
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # ── Check if already seeded ───────────────────────────────────────────
        existing = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        if existing.scalar_one_or_none():
            print("⚠️  Demo user already exists. Skipping seed.")
            print(f"   Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
            return

        print("🌱 Seeding database...")

        # ── Workspace ─────────────────────────────────────────────────────────
        workspace = Workspace(
            id=uuid.uuid4(),
            name="Demo Workspace",
            slug="demo-workspace",
            plan="free",
        )
        db.add(workspace)
        await db.flush()
        print(f"   ✅ Workspace:  {workspace.name} ({workspace.id})")

        # ── User ──────────────────────────────────────────────────────────────
        user = User(
            id=uuid.uuid4(),
            email=DEMO_EMAIL,
            name=DEMO_NAME,
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        await db.flush()

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )
        db.add(member)
        print(f"   ✅ User:       {user.email} (password: {DEMO_PASSWORD})")

        # ── QA Dataset ────────────────────────────────────────────────────────
        qa_dataset = Dataset(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            name="General Knowledge QA",
            description="10 factual Q&A pairs — good for testing factual accuracy",
            type="qa",
            row_count=len(QA_ROWS),
            created_by=user.id,
        )
        db.add(qa_dataset)
        await db.flush()

        for prompt, expected in QA_ROWS:
            db.add(DatasetRow(
                id=uuid.uuid4(),
                dataset_id=qa_dataset.id,
                input_prompt=prompt,
                expected_output=expected,
                tags=["factual", "general-knowledge"],
            ))
        print(f"   ✅ Dataset:    '{qa_dataset.name}' ({len(QA_ROWS)} rows)")

        # ── Factual Dataset ───────────────────────────────────────────────────
        factual_dataset = Dataset(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            name="Tech Concepts Factual",
            description="5 technical definition prompts for hallucination testing",
            type="factual",
            row_count=len(FACTUAL_ROWS),
            created_by=user.id,
        )
        db.add(factual_dataset)
        await db.flush()

        for prompt, expected in FACTUAL_ROWS:
            db.add(DatasetRow(
                id=uuid.uuid4(),
                dataset_id=factual_dataset.id,
                input_prompt=prompt,
                expected_output=expected,
                tags=["tech", "definitions"],
            ))
        print(f"   ✅ Dataset:    '{factual_dataset.name}' ({len(FACTUAL_ROWS)} rows)")

        # ── Model Endpoint ────────────────────────────────────────────────────
        # Uses a placeholder key — replace with real key to run actual evals
        api_key = settings.openai_api_key or "sk-replace-with-real-key"
        model = ModelEndpoint(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            name="GPT-4o-mini (Demo)",
            provider="openai",
            base_url="https://api.openai.com/v1",
            model_name="gpt-4o-mini",
            api_key_encrypted=encrypt_api_key(api_key),
            system_prompt="You are a helpful, accurate assistant. Always give concise, factual answers.",
            temperature=0.0,
            max_tokens=500,
        )
        db.add(model)
        print(f"   ✅ Model:      {model.name}")

        # ── Alert Rule ────────────────────────────────────────────────────────
        alert = AlertRule(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            name="Low overall score",
            metric="overall_score",
            operator="lt",
            threshold=70.0,
            notify_email=[DEMO_EMAIL],
            enabled=True,
        )
        db.add(alert)
        print(f"   ✅ Alert:      '{alert.name}' (overall_score < 70)")

        await db.commit()

        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅  Seed complete!")
        print()
        print("  Login URL:  http://localhost:3000/login")
        print(f"  Email:      {DEMO_EMAIL}")
        print(f"  Password:   {DEMO_PASSWORD}")
        print()
        print("  Next steps:")
        print("  1. Add your OPENAI_API_KEY to .env")
        print("  2. Go to Models → update the demo endpoint API key")
        print("  3. Create a new eval run using 'General Knowledge QA'")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(seed())
