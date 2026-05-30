"""
EvalForge DB Management CLI
Usage:
    python manage.py migrate          # Run all pending migrations
    python manage.py migrate --check  # Check pending migrations without running
    python manage.py seed             # Populate demo data
    python manage.py reset            # Drop all tables + re-migrate + seed
    python manage.py status           # Show current migration status
    python manage.py makemigration    # Auto-generate a new migration from model changes
"""
import sys
import os
import subprocess
import asyncio

sys.path.insert(0, os.path.dirname(__file__))


def run_alembic(*args):
    """Run an alembic CLI command."""
    result = subprocess.run(
        ["alembic"] + list(args),
        cwd=os.path.dirname(__file__),
    )
    return result.returncode


def cmd_migrate(check=False):
    print("🔄 Running migrations...")
    if check:
        code = run_alembic("upgrade", "head", "--sql")
    else:
        code = run_alembic("upgrade", "head")
    if code == 0:
        print("✅ Migrations complete")
    else:
        print("❌ Migration failed")
        sys.exit(1)


def cmd_status():
    print("📋 Migration status:")
    run_alembic("current")
    print()
    print("📋 Migration history:")
    run_alembic("history", "--verbose")


def cmd_seed():
    from seed import seed
    asyncio.run(seed())


def cmd_reset():
    print("⚠️  This will DROP ALL TABLES and re-migrate.")
    confirm = input("Type 'yes' to confirm: ").strip()
    if confirm != "yes":
        print("Aborted.")
        return

    print("🗑️  Dropping all tables...")
    run_alembic("downgrade", "base")

    print("🔄 Re-running migrations...")
    run_alembic("upgrade", "head")

    print("🌱 Seeding...")
    cmd_seed()


def cmd_makemigration(message="auto"):
    print(f"🔧 Generating migration: {message}")
    run_alembic("revision", "--autogenerate", "-m", message)
    print("✅ Migration file created in alembic/versions/")
    print("   Review it before running 'python manage.py migrate'")


if __name__ == "__main__":
    commands = {
        "migrate": cmd_migrate,
        "status": cmd_status,
        "seed": cmd_seed,
        "reset": cmd_reset,
        "makemigration": cmd_makemigration,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    kwargs = {}

    if cmd == "migrate" and "--check" in sys.argv:
        kwargs["check"] = True
    if cmd == "makemigration" and len(sys.argv) > 2:
        kwargs["message"] = sys.argv[2]

    commands[cmd](**kwargs)
