from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from .models import User
from .store import InMemoryStudyLabStore

# Password hashing parameters. PBKDF2-HMAC-SHA256 is in the Python stdlib, so the
# core stays dependency-light while using a real, salted, slow KDF.
_PBKDF2_ALGO = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 200_000

# JWT settings. We implement a minimal HS256 JWT with stdlib hmac so there is no
# external dependency; tokens are stateless and verified by signature + expiry.
_JWT_ALG = "HS256"
_DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # 7 days
_DEV_SECRET = "studylab-dev-secret-change-me"


class AuthError(Exception):
    """Raised for invalid credentials, malformed/expired tokens, or duplicate signups."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def hash_password(password: str, *, salt: bytes | None = None, iterations: int = _PBKDF2_ITERATIONS) -> str:
    if not password:
        raise AuthError("password must not be empty")
    salt = salt if salt is not None else os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_PBKDF2_ALGO}${iterations}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != _PBKDF2_ALGO:
            return False
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(derived.hex(), hash_hex)


def make_auth_secret() -> str:
    """Resolve the JWT signing secret from the environment, with a dev fallback."""
    return os.getenv("STUDYLAB_JWT_SECRET") or _DEV_SECRET


class AuthEngine:
    """User registration, login, and stateless JWT issuance/verification.

    Auth is additive and **opt-in**: the engine and its endpoints always work, but
    the gateway only *enforces* a bearer token when ``STUDYLAB_REQUIRE_AUTH`` is set,
    so existing offline/demo flows (and the test suite) keep running unchanged.
    """

    def __init__(self, store: InMemoryStudyLabStore, secret: str | None = None, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        self.store = store
        self.secret = secret or make_auth_secret()
        self.ttl_seconds = ttl_seconds

    # ── Registration / login ─────────────────────────────────────────────

    def register(self, email: str, password: str, subject_domain: str = "ai_ds") -> User:
        normalized = self._normalize_email(email)
        if self.store.get_user_by_email(normalized) is not None:
            raise AuthError("an account with this email already exists")
        if len(password) < 8:
            raise AuthError("password must be at least 8 characters")
        user = User(
            id=self.store.next_id("user"),
            email=normalized,
            password_hash=hash_password(password),
            subject_domain=subject_domain,
        )
        return self.store.add_user(user)

    def login(self, email: str, password: str) -> dict[str, Any]:
        user = self.store.get_user_by_email(self._normalize_email(email))
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("invalid email or password")
        return {"token": self.issue_token(user), "token_type": "Bearer", "user": self._public_user(user)}

    # ── Token issue / verify ─────────────────────────────────────────────

    def issue_token(self, user: User) -> str:
        now = int(time.time())
        header = {"alg": _JWT_ALG, "typ": "JWT"}
        payload = {"sub": user.id, "email": user.email, "iat": now, "exp": now + self.ttl_seconds}
        segments = [
            _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
        signature = self._sign(".".join(segments))
        segments.append(_b64url_encode(signature))
        return ".".join(segments)

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            header_seg, payload_seg, signature_seg = token.split(".")
        except (ValueError, AttributeError) as exc:
            raise AuthError("malformed token") from exc
        expected = self._sign(f"{header_seg}.{payload_seg}")
        if not hmac.compare_digest(expected, _b64url_decode(signature_seg)):
            raise AuthError("invalid token signature")
        try:
            payload = json.loads(_b64url_decode(payload_seg))
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthError("malformed token payload") from exc
        if int(payload.get("exp", 0)) < int(time.time()):
            raise AuthError("token expired")
        return payload

    def user_from_token(self, token: str) -> User:
        payload = self.decode_token(token)
        user = self.store.users.get(payload.get("sub"))
        if user is None:
            raise AuthError("token subject no longer exists")
        return user

    def public_user(self, user: User) -> dict[str, Any]:
        return self._public_user(user)

    # ── internals ────────────────────────────────────────────────────────

    def _sign(self, signing_input: str) -> bytes:
        return hmac.new(self.secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized = (email or "").strip().lower()
        if "@" not in normalized or "." not in normalized.split("@")[-1]:
            raise AuthError("a valid email is required")
        return normalized

    @staticmethod
    def _public_user(user: User) -> dict[str, Any]:
        """User view safe to return to clients — never includes the password hash."""
        return {
            "id": user.id,
            "email": user.email,
            "subject_domain": user.subject_domain,
            "prefs": user.prefs,
            "created_at": user.created_at,
        }
