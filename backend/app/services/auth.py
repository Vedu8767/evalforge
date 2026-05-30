from datetime import datetime, timedelta
from typing import Optional
import base64
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Password ────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── JWT ─────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# ─── API Key Encryption ───────────────────────────────────────────────────────
# We use Fernet (AES-128-CBC + HMAC) symmetric encryption.
# The encryption key lives only in env vars — never in the DB.

def _get_fernet() -> Fernet:
    """Derive a Fernet key from the configured ENCRYPTION_KEY."""
    raw = settings.encryption_key.encode()
    # Pad or truncate to 32 bytes, then base64-urlsafe encode for Fernet
    key_bytes = raw[:32].ljust(32, b"0")
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage."""
    f = _get_fernet()
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    """Decrypt a stored API key for use in LLM calls."""
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


def mask_api_key(api_key: str) -> str:
    """Return a masked version safe to show in UI. e.g. sk-...****"""
    if len(api_key) <= 8:
        return "****"
    return api_key[:5] + "..." + "****"
