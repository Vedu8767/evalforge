"""
DB Health Check
Verifies everything is set up correctly before starting the app.

Usage: python check_db.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.config import settings


async def check():
    print("🔍 EvalForge — DB Health Check")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    all_ok = True

    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # ── 1. Basic connection ───────────────────────────────────────────────────
    try:
        async with Session() as db:
            result = await db.execute(text("SELECT version()"))
            version = result.scalar()
            pg_version = version.split(",")[0] if version else "unknown"
            print(f"✅ PostgreSQL connected: {pg_version}")
    except Exception as e:
        print(f"❌ Cannot connect to PostgreSQL: {e}")
        print(f"   DATABASE_URL: {settings.database_url[:40]}...")
        print()
        print("   Fix: Is docker-compose running?")
        print("   Run: docker-compose up -d")
        all_ok = False

    if not all_ok:
        sys.exit(1)

    async with Session() as db:
        # ── 2. pgvector extension ─────────────────────────────────────────────
        try:
            result = await db.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
            version = result.scalar()
            if version:
                print(f"✅ pgvector extension: v{version}")
            else:
                print("⚠️  pgvector not installed — run migrations first")
                print("   Run: alembic upgrade head")
                all_ok = False
        except Exception as e:
            print(f"❌ pgvector check failed: {e}")
            all_ok = False

        # ── 3. Tables exist ───────────────────────────────────────────────────
        expected_tables = [
            "workspaces", "users", "workspace_members",
            "model_endpoints", "datasets", "dataset_rows",
            "eval_runs", "eval_results", "baselines", "alert_rules",
        ]
        try:
            result = await db.execute(
                text("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """)
            )
            existing_tables = {row[0] for row in result.fetchall()}
            missing = [t for t in expected_tables if t not in existing_tables]

            if missing:
                print(f"❌ Missing tables: {', '.join(missing)}")
                print("   Run: alembic upgrade head")
                all_ok = False
            else:
                print(f"✅ All {len(expected_tables)} tables exist")
        except Exception as e:
            print(f"❌ Table check failed: {e}")
            all_ok = False

        # ── 4. Indexes exist ──────────────────────────────────────────────────
        try:
            result = await db.execute(
                text("""
                    SELECT indexname FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND indexname LIKE 'ix_%'
                    ORDER BY indexname
                """)
            )
            indexes = [row[0] for row in result.fetchall()]
            print(f"✅ {len(indexes)} performance indexes found")
            hnsw = [i for i in indexes if "hnsw" in i]
            if hnsw:
                print(f"   Including HNSW vector index: {hnsw[0]}")
        except Exception as e:
            print(f"⚠️  Index check failed: {e}")

        # ── 5. Alembic version ────────────────────────────────────────────────
        try:
            result = await db.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
            )
            version = result.scalar()
            print(f"✅ Alembic version: {version}")
        except Exception as e:
            print(f"⚠️  No alembic version table found — run migrations first")
            all_ok = False

        # ── 6. Row counts ─────────────────────────────────────────────────────
        try:
            counts = {}
            for table in ["workspaces", "users", "datasets", "eval_runs"]:
                r = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                counts[table] = r.scalar()
            print(f"📊 Row counts: {counts}")
            if counts["users"] == 0:
                print("   Tip: Run 'python seed.py' to create demo data")
        except Exception as e:
            print(f"⚠️  Row count check: {e}")

        # ── 7. Redis connection ───────────────────────────────────────────────
        try:
            import redis
            r = redis.from_url(settings.redis_url)
            r.ping()
            print(f"✅ Redis connected: {settings.redis_url}")
        except Exception as e:
            print(f"❌ Redis not reachable: {e}")
            print("   Run: docker-compose up -d")
            all_ok = False

    await engine.dispose()

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if all_ok:
        print("✅ All checks passed — ready to start!")
        print()
        print("  Start API:    uvicorn app.main:app --reload --port 8000")
        print("  Start worker: celery -A celery_worker worker --loglevel=info")
    else:
        print("❌ Some checks failed — fix issues above before starting")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check())
