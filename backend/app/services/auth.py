"""
Auth Service — password hashing (direct bcrypt, no passlib)
JWT creation/verification, API key encryption
"""
import bcrypt
import jwt
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import base64
import hashlib

from app.config import settings


# ─── Password hashing (bcrypt directly — no passlib) ──────────────────────────

def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    pw_bytes = password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except (ValueError, AttributeError):
        return False


# ─── JWT ────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.jwt_expire_minutes
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


# Backward-compatible alias
decode_access_token = decode_token


# ─── API key encryption (AES-256 via Fernet) ──────────────────────────────────

def _get_fernet() -> Fernet:
    key_bytes = settings.encryption_key.encode("utf-8")
    digest = hashlib.sha256(key_bytes).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_api_key(plain_key: str) -> str:
    f = _get_fernet()
    return f.encrypt(plain_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    f = _get_fernet()
    return f.decrypt(encrypted_key.encode("utf-8")).decode("utf-8")


def mask_api_key(plain_key: str) -> str:
    """Return a masked version of an API key for display in the UI,
    e.g. 'gsk_abc123...xyz9' -> 'gsk_...xyz9'. Never expose the full key."""
    if not plain_key or len(plain_key) <= 8:
        return "••••••••"
    return f"{plain_key[:4]}...{plain_key[-4:]}"
