"""
EvalForge — Pure Unit Tests (no database, no Docker needed)
Run: pytest tests/test_unit.py -v
"""
import pytest
from uuid import uuid4


# ─── Password Hashing ────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_returns_string(self):
        from app.services.auth import hash_password
        assert isinstance(hash_password("testpassword123"), str)

    def test_hash_is_not_plaintext(self):
        from app.services.auth import hash_password
        assert hash_password("secret") != "secret"

    def test_verify_correct_password(self):
        from app.services.auth import hash_password, verify_password
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        from app.services.auth import hash_password, verify_password
        h = hash_password("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_long_password_no_crash(self):
        from app.services.auth import hash_password, verify_password
        pw = "a" * 100
        h = hash_password(pw)
        assert verify_password(pw, h) is True

    def test_different_hashes_same_input(self):
        from app.services.auth import hash_password
        assert hash_password("password") != hash_password("password")


# ─── JWT ─────────────────────────────────────────────────────────────────────

class TestJWT:
    def test_create_and_decode(self):
        from app.services.auth import create_access_token, decode_token
        data = {"sub": str(uuid4()), "email": "test@test.com", "workspace_id": str(uuid4())}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == data["sub"]
        assert decoded["email"] == data["email"]

    def test_invalid_token_returns_none(self):
        from app.services.auth import decode_token
        assert decode_token("invalid.token.here") is None

    def test_empty_token_returns_none(self):
        from app.services.auth import decode_token
        assert decode_token("") is None

    def test_tampered_token_returns_none(self):
        from app.services.auth import create_access_token, decode_token
        token = create_access_token({"sub": "123"})
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None


# ─── Encryption ───────────────────────────────────────────────────────────────

class TestEncryption:
    def test_roundtrip(self):
        from app.services.auth import encrypt_api_key, decrypt_api_key
        original = "sk-test-api-key-12345"
        assert decrypt_api_key(encrypt_api_key(original)) == original

    def test_encrypted_differs(self):
        from app.services.auth import encrypt_api_key
        key = "sk-test-api-key"
        assert encrypt_api_key(key) != key

    def test_mask_short_key(self):
        from app.services.auth import mask_api_key
        assert mask_api_key("short") == "••••••••"

    def test_mask_long_key(self):
        from app.services.auth import mask_api_key
        result = mask_api_key("sk-1234567890abcdef")
        assert "..." in result
        assert len(result) < len("sk-1234567890abcdef")

    def test_mask_empty_key(self):
        from app.services.auth import mask_api_key
        assert mask_api_key("") == "••••••••"


# ─── Embeddings ───────────────────────────────────────────────────────────────

class TestEmbeddings:
    def test_hash_embed_correct_dimension(self):
        from app.services.embeddings import _hash_embed, EMBEDDING_DIM
        assert len(_hash_embed("test text")) == EMBEDDING_DIM

    def test_hash_embed_is_normalized(self):
        import numpy as np
        from app.services.embeddings import _hash_embed
        vec = _hash_embed("test text")
        assert abs(np.linalg.norm(vec) - 1.0) < 1e-6

    def test_hash_embed_deterministic(self):
        from app.services.embeddings import _hash_embed
        assert _hash_embed("hello") == _hash_embed("hello")

    def test_cosine_similarity_identical(self):
        from app.services.embeddings import cosine_similarity
        vec = [1.0, 0.0, 0.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        from app.services.embeddings import cosine_similarity
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_cosine_similarity_opposite(self):
        from app.services.embeddings import cosine_similarity
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_average_pairwise_single_vector(self):
        from app.services.embeddings import average_pairwise_similarity
        assert average_pairwise_similarity([[1.0, 0.0]]) == 1.0

    def test_average_pairwise_identical_vectors(self):
        from app.services.embeddings import average_pairwise_similarity
        vec = [1.0, 0.0, 0.0]
        assert average_pairwise_similarity([vec, vec, vec]) == pytest.approx(1.0)

    def test_average_pairwise_different_vectors(self):
        from app.services.embeddings import average_pairwise_similarity
        v1, v2 = [1.0, 0.0], [0.0, 1.0]
        score = average_pairwise_similarity([v1, v2])
        assert 0.0 <= score <= 1.0


# ─── Config ───────────────────────────────────────────────────────────────────

class TestConfig:
    def test_settings_loads(self):
        from app.config import settings
        assert settings is not None

    def test_jwt_algorithm(self):
        from app.config import settings
        assert settings.jwt_algorithm == "HS256"

    def test_expire_minutes_positive(self):
        from app.config import settings
        assert settings.jwt_expire_minutes > 0

    def test_required_fields_exist(self):
        from app.config import settings
        for field in ["database_url", "redis_url", "jwt_secret", "encryption_key"]:
            assert hasattr(settings, field)


# ─── Mask API Key edge cases ──────────────────────────────────────────────────

class TestMaskApiKey:
    def test_exact_8_chars(self):
        from app.services.auth import mask_api_key
        assert mask_api_key("12345678") == "••••••••"

    def test_9_chars_shows_mask(self):
        from app.services.auth import mask_api_key
        result = mask_api_key("123456789")
        assert "..." in result

    def test_groq_key_format(self):
        from app.services.auth import mask_api_key
        result = mask_api_key("gsk_abc123xyz789")
        assert result.startswith("gsk_")
        assert result.endswith("789")
        assert "..." in result
