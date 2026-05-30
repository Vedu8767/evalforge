"""
EvalForge Backend Tests
Run: pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db import get_db, Base
from app.config import settings

# ─── Test DB setup ────────────────────────────────────────────────────────────

TEST_DB_URL = settings.database_url.replace("/evalforge", "/evalforge_test")

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        try:
            await conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ─── Helper ───────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, email="test@example.com", password="password123", name="Test User"):
    resp = await client.post("/auth/register", json={"email": email, "password": password, "name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


# ─── Auth Tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/auth/register", json={
        "email": "new@example.com", "password": "securepass", "name": "New User"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "pass1234", "name": "User"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/auth/register", json={
        "email": "login@example.com", "password": "mypassword", "name": "Login User"
    })
    resp = await client.post("/auth/login", json={
        "email": "login@example.com", "password": "mypassword"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/auth/register", json={
        "email": "wp@example.com", "password": "correctpass", "name": "User"
    })
    resp = await client.post("/auth/login", json={"email": "wp@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client):
    token = await register_and_login(client)
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_me_no_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no token


# ─── Health Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── Model Endpoint Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_model_endpoint(client):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/model-endpoints", headers=headers, json={
        "name": "Test GPT-4o",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4o",
        "api_key": "sk-test-key-12345",
        "temperature": 0.0,
        "max_tokens": 500,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test GPT-4o"
    assert "sk-test" in data["api_key_masked"]
    assert "api_key" not in data          # raw key must never be returned


@pytest.mark.asyncio
async def test_list_model_endpoints(client):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create two endpoints
    for i in range(2):
        await client.post("/model-endpoints", headers=headers, json={
            "name": f"Model {i}", "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o-mini", "api_key": f"sk-key-{i}",
        })

    resp = await client.get("/model-endpoints", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_delete_model_endpoint(client):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/model-endpoints", headers=headers, json={
        "name": "To Delete", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4o", "api_key": "sk-delete-me",
    })
    endpoint_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/model-endpoints/{endpoint_id}", headers=headers)
    assert del_resp.status_code == 204

    list_resp = await client.get("/model-endpoints", headers=headers)
    assert len(list_resp.json()) == 0


# ─── Dataset Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_dataset(client):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/datasets", headers=headers, json={
        "name": "QA Test Set", "type": "qa", "description": "My first dataset"
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "QA Test Set"
    assert resp.json()["row_count"] == 0


@pytest.mark.asyncio
async def test_add_rows_to_dataset(client):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    ds_resp = await client.post("/datasets", headers=headers, json={"name": "DS", "type": "qa"})
    ds_id = ds_resp.json()["id"]

    rows_resp = await client.post(f"/datasets/{ds_id}/rows", headers=headers, json={
        "rows": [
            {"input_prompt": "What is 2+2?", "expected_output": "4"},
            {"input_prompt": "Capital of France?", "expected_output": "Paris"},
        ]
    })
    assert rows_resp.status_code == 201
    assert len(rows_resp.json()) == 2

    # Verify row_count updated
    ds_check = await client.get(f"/datasets/{ds_id}", headers=headers)
    assert ds_check.json()["row_count"] == 2


@pytest.mark.asyncio
async def test_upload_csv(client):
    import io
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    ds_resp = await client.post("/datasets", headers=headers, json={"name": "CSV DS", "type": "factual"})
    ds_id = ds_resp.json()["id"]

    csv_content = "input_prompt,expected_output\nWhat is Python?,A programming language\nWhat is FastAPI?,A web framework\n"
    resp = await client.post(
        f"/datasets/{ds_id}/upload",
        headers=headers,
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 201
    assert resp.json()["rows_created"] == 2


# ─── Eval Run Tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_eval_run(client):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Setup: create model + dataset
    model_resp = await client.post("/model-endpoints", headers=headers, json={
        "name": "Test Model", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4o-mini", "api_key": "sk-test",
    })
    model_id = model_resp.json()["id"]

    ds_resp = await client.post("/datasets", headers=headers, json={"name": "Eval DS", "type": "qa"})
    ds_id = ds_resp.json()["id"]
    await client.post(f"/datasets/{ds_id}/rows", headers=headers, json={
        "rows": [{"input_prompt": "Hello?", "expected_output": "Hi!"}]
    })

    run_resp = await client.post("/eval-runs", headers=headers, json={
        "dataset_id": ds_id,
        "model_endpoint_id": model_id,
        "eval_types": ["factual"],
        "concurrency": 1,
    })
    assert run_resp.status_code == 201
    data = run_resp.json()
    assert data["status"] == "queued"
    assert data["eval_types"] == ["factual"]


@pytest.mark.asyncio
async def test_list_eval_runs(client):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/eval-runs", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── Alert Tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_alert_rule(client):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/alerts", headers=headers, json={
        "name": "Low overall score",
        "metric": "overall_score",
        "operator": "lt",
        "threshold": 70.0,
        "notify_email": ["admin@example.com"],
    })
    assert resp.status_code == 201
    assert resp.json()["metric"] == "overall_score"
    assert resp.json()["threshold"] == 70.0


@pytest.mark.asyncio
async def test_alert_invalid_metric(client):
    token = await register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/alerts", headers=headers, json={
        "name": "Bad alert", "metric": "nonexistent_metric",
        "operator": "lt", "threshold": 50.0,
    })
    assert resp.status_code == 400


# ─── Encryption Tests ─────────────────────────────────────────────────────────

def test_api_key_encrypt_decrypt():
    from app.services.auth import encrypt_api_key, decrypt_api_key
    original = "sk-super-secret-key-12345"
    encrypted = encrypt_api_key(original)
    assert encrypted != original
    assert decrypt_api_key(encrypted) == original


def test_api_key_mask():
    from app.services.auth import mask_api_key
    assert mask_api_key("sk-abcdefghijklmnop") == "sk-ab...****"
    assert mask_api_key("short") == "****"


# ─── Embedding Tests ──────────────────────────────────────────────────────────

def test_cosine_similarity():
    from app.services.embeddings import cosine_similarity
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(1.0)

    c = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, c) == pytest.approx(0.0)


def test_average_pairwise_similarity():
    from app.services.embeddings import average_pairwise_similarity
    embs = [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]]
    assert average_pairwise_similarity(embs) == pytest.approx(1.0)
