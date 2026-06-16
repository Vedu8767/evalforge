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
    # bcrypt has a 72-byte limit; truncate safely if needed
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
    """Decode and verify a JWT. Returns None if invalid/expired instead of raising,
    since routers/auth.py checks `if not payload:` rather than catching exceptions."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


# Backward-compatible alias in case any other file imports the old name
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
