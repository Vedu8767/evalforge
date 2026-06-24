"""
EvalForge — Unit & Integration Tests
Run: pytest tests/ -v
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ─── Auth Service Tests ───────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_password_returns_string(self):
        from app.services.auth import hash_password
        result = hash_password("testpassword123")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_is_not_plaintext(self):
        from app.services.auth import hash_password
        result = hash_password("testpassword123")
        assert result != "testpassword123"

    def test_verify_correct_password(self):
        from app.services.auth import hash_password, verify_password
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        from app.services.auth import hash_password, verify_password
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_handles_long_password(self):
        """bcrypt truncates at 72 bytes — should not crash."""
        from app.services.auth import hash_password, verify_password
        long_pw = "a" * 100
        hashed = hash_password(long_pw)
        assert verify_password(long_pw, hashed) is True

    def test_different_hashes_for_same_password(self):
        """bcrypt uses random salt — same input, different output."""
        from app.services.auth import hash_password
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert h1 != h2


class TestJWT:
    def test_create_and_decode_token(self):
        from app.services.auth import create_access_token, decode_token
        data = {"sub": str(uuid4()), "email": "test@test.com", "workspace_id": str(uuid4())}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == data["sub"]
        assert decoded["email"] == data["email"]

    def test_invalid_token_returns_none(self):
        from app.services.auth import decode_token
        result = decode_token("invalid.token.here")
        assert result is None

    def test_empty_token_returns_none(self):
        from app.services.auth import decode_token
        result = decode_token("")
        assert result is None


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        from app.services.auth import encrypt_api_key, decrypt_api_key
        original = "sk-test-api-key-12345"
        encrypted = encrypt_api_key(original)
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original

    def test_encrypted_differs_from_original(self):
        from app.services.auth import encrypt_api_key
        key = "sk-test-api-key"
        encrypted = encrypt_api_key(key)
        assert encrypted != key

    def test_mask_api_key_short(self):
        from app.services.auth import mask_api_key
        result = mask_api_key("short")
        assert result == "••••••••"

    def test_mask_api_key_normal(self):
        from app.services.auth import mask_api_key
        result = mask_api_key("sk-1234567890abcdef")
        assert result == "sk-1...cdef"
        assert "..." in result


# ─── LLM Client Tests ─────────────────────────────────────────────────────────

class TestLLMClient:
    @pytest.mark.asyncio
    async def test_call_llm_returns_response_on_success(self):
        from app.services.llm_client import LLMResponse

        mock_endpoint = MagicMock()
        mock_endpoint.provider = "custom"
        mock_endpoint.base_url = "https://api.groq.com/openai/v1"
        mock_endpoint.model_name = "llama-3.1-8b-instant"
        mock_endpoint.temperature = 0.1
        mock_endpoint.max_tokens = 100
        mock_endpoint.system_prompt = None
        mock_endpoint.api_key_encrypted = "dummy"

        mock_response_data = {
            "choices": [{"message": {"content": "Paris is the capital of France."}}],
            "usage": {"total_tokens": 20},
            "model": "llama-3.1-8b-instant"
        }

        with patch("app.services.auth.decrypt_api_key", return_value="test-key"), \
             patch("httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response_data
            mock_resp.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.post = AsyncMock(return_value=mock_resp)

            from app.services.llm_client import _call_openai_compat
            import time
            result = await _call_openai_compat(
                "What is the capital of France?",
                "You are helpful.",
                mock_endpoint,
                "test-key",
                time.monotonic()
            )

            assert isinstance(result, LLMResponse)
            assert result.content == "Paris is the capital of France."
            assert result.error is None
            assert result.tokens_used == 20

    @pytest.mark.asyncio
    async def test_call_llm_handles_error_gracefully(self):
        from app.services.llm_client import call_llm

        mock_endpoint = MagicMock()
        mock_endpoint.provider = "custom"
        mock_endpoint.base_url = "https://api.invalid.com/v1"
        mock_endpoint.model_name = "test-model"
        mock_endpoint.temperature = 0.1
        mock_endpoint.max_tokens = 100
        mock_endpoint.system_prompt = None
        mock_endpoint.api_key_encrypted = "dummy"

        with patch("app.services.auth.decrypt_api_key", return_value="test-key"), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.post = AsyncMock(side_effect=Exception("Connection refused"))

            result = await call_llm("test prompt", mock_endpoint)
            assert result.error is not None
            assert result.content == ""


# ─── Factual Scoring Tests ────────────────────────────────────────────────────

class TestFactualScoring:
    @pytest.mark.asyncio
    async def test_factual_result_has_required_fields(self):
        from app.services.eval_engine.factual import FactualResult
        result = FactualResult(
            factual_score=0.9,
            verdict="correct",
            judge_reasoning="The answer is accurate.",
            missing_facts=[],
            extra_facts=[]
        )
        assert result.factual_score == 0.9
        assert result.verdict == "correct"

    @pytest.mark.asyncio
    async def test_factual_check_handles_judge_error(self):
        """If the judge fails, should return 0.0 not crash."""
        from app.services.eval_engine.factual import check_factual_accuracy

        mock_endpoint = MagicMock()

        with patch("app.services.eval_engine.factual.call_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "invalid json {"
            mock_response.error = None
            mock_llm.return_value = mock_response

            result = await check_factual_accuracy(
                question="What is 2+2?",
                actual_output="4",
                endpoint=mock_endpoint,
                expected_output="4"
            )
            # Should not crash — returns degraded result
            assert result.factual_score == 0.0


# ─── Embeddings Tests ─────────────────────────────────────────────────────────

class TestEmbeddings:
    def test_hash_embed_returns_correct_dimension(self):
        from app.services.embeddings import _hash_embed, EMBEDDING_DIM
        result = _hash_embed("test text")
        assert len(result) == EMBEDDING_DIM

    def test_hash_embed_is_normalized(self):
        import numpy as np
        from app.services.embeddings import _hash_embed
        result = _hash_embed("test text")
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6  # unit vector

    def test_cosine_similarity_identical(self):
        from app.services.embeddings import cosine_similarity
        vec = [1.0, 0.0, 0.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        from app.services.embeddings import cosine_similarity
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(0.0)

    def test_cosine_similarity_opposite(self):
        from app.services.embeddings import cosine_similarity
        vec_a = [1.0, 0.0]
        vec_b = [-1.0, 0.0]
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(-1.0)

    def test_average_pairwise_similarity_single(self):
        from app.services.embeddings import average_pairwise_similarity
        result = average_pairwise_similarity([[1.0, 0.0]])
        assert result == 1.0

    def test_average_pairwise_similarity_identical(self):
        from app.services.embeddings import average_pairwise_similarity
        vec = [1.0, 0.0, 0.0]
        result = average_pairwise_similarity([vec, vec, vec])
        assert result == pytest.approx(1.0)


# ─── Config Tests ─────────────────────────────────────────────────────────────

class TestConfig:
    def test_settings_loads(self):
        from app.config import settings
        assert settings is not None
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_expire_minutes > 0

    def test_settings_has_required_fields(self):
        from app.config import settings
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_url")
        assert hasattr(settings, "jwt_secret")
        assert hasattr(settings, "encryption_key")
