from __future__ import annotations

import base64
import binascii
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
    """Resolve the JWT signing secret from the environment.

    Production safety: when auth is being *enforced* (``STUDYLAB_REQUIRE_AUTH``), a real
    ``STUDYLAB_JWT_SECRET`` is mandatory — we refuse to start on the public dev sentinel so
    tokens can't be forged. With enforcement off (offline/demo/tests) the dev fallback is
    allowed, unless ``STUDYLAB_DEV_INSECURE`` is explicitly set to keep it even with auth on.
    """
    secret = os.getenv("STUDYLAB_JWT_SECRET")
    enforce = (os.getenv("STUDYLAB_REQUIRE_AUTH") or "").strip().lower() in {"1", "true", "yes", "on"}
    dev_ok = (os.getenv("STUDYLAB_DEV_INSECURE") or "").strip().lower() in {"1", "true", "yes", "on"}
    if secret and secret != _DEV_SECRET:
        return secret
    if enforce and not dev_ok:
        raise RuntimeError(
            "STUDYLAB_JWT_SECRET must be set to a strong, non-default value when "
            "STUDYLAB_REQUIRE_AUTH is enabled (set STUDYLAB_DEV_INSECURE=1 to override in dev only)."
        )
    return _DEV_SECRET


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _mock_email_enabled() -> bool:
    """Reset tokens are only returned in the API response in mock-email mode.

    Mock mode = auth not enforced (offline/demo/tests) OR an explicit opt-in flag. In a
    real (enforced) deployment the token must be emailed, never returned to the caller.
    """
    enforce = _truthy(os.getenv("STUDYLAB_REQUIRE_AUTH"))
    return not enforce or _truthy(os.getenv("STUDYLAB_AUTH_MOCK_EMAIL"))


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

    def issue_token(self, user: User, purpose: str = "session", ttl_seconds: int | None = None) -> str:
        now = int(time.time())
        header = {"alg": _JWT_ALG, "typ": "JWT"}
        payload = {
            "sub": user.id,
            "email": user.email,
            "purpose": purpose,
            "iat": now,
            "exp": now + (ttl_seconds if ttl_seconds is not None else self.ttl_seconds),
        }
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
        try:
            signature = _b64url_decode(signature_seg)
        except (ValueError, binascii.Error) as exc:
            raise AuthError("malformed token signature") from exc
        expected = self._sign(f"{header_seg}.{payload_seg}")
        if not hmac.compare_digest(expected, signature):
            raise AuthError("invalid token signature")
        try:
            payload = json.loads(_b64url_decode(payload_seg))
            expiry = int(payload.get("exp", 0))
        except (ValueError, binascii.Error, json.JSONDecodeError) as exc:
            raise AuthError("malformed token payload") from exc
        if expiry < int(time.time()):
            raise AuthError("token expired")
        return payload

    def user_from_token(self, token: str, expected_purpose: str = "session") -> User:
        payload = self.decode_token(token)
        if payload.get("purpose", "session") != expected_purpose:
            raise AuthError("token cannot be used for this action")
        user = self.store.users.get(payload.get("sub"))
        if user is None:
            raise AuthError("token subject no longer exists")
        return user

    def public_user(self, user: User) -> dict[str, Any]:
        return self._public_user(user)

    # ── Account self-service (Phase 6) ────────────────────────────────────

    def change_password(self, user_id: str, current_password: str, new_password: str) -> dict[str, Any]:
        user = self.store.require_user(user_id)
        if not verify_password(current_password, user.password_hash):
            raise AuthError("current password is incorrect")
        if len(new_password) < 8:
            raise AuthError("password must be at least 8 characters")
        user.password_hash = hash_password(new_password)
        self.store.save_user(user)
        return self._public_user(user)

    def update_profile(self, user_id: str, subject_domain: str | None = None, prefs: dict | None = None) -> dict[str, Any]:
        user = self.store.require_user(user_id)
        if subject_domain is not None:
            user.subject_domain = subject_domain
        if prefs is not None:
            user.prefs = prefs
        self.store.save_user(user)
        return self._public_user(user)

    def request_password_reset(self, email: str) -> dict[str, Any]:
        """Issue a short-lived, purpose-scoped reset token.

        Security: the token is returned in the response **only in mock-email mode** — i.e. when
        auth is not being enforced (offline/demo/tests) or ``STUDYLAB_AUTH_MOCK_EMAIL`` is set.
        In production (``STUDYLAB_REQUIRE_AUTH`` on, no mock flag) the token is created but a real
        deployment must deliver it out-of-band (email); the response only confirms receipt, so a
        public caller can never read another account's reset token. The response shape is identical
        whether or not the email exists, to avoid account enumeration.
        """
        user = self.store.get_user_by_email(self._normalize_email(email))
        token = self.issue_token(user, purpose="pwreset", ttl_seconds=30 * 60) if user else None
        return {"ok": True, "reset_token": token if _mock_email_enabled() else None}

    def reset_password(self, token: str, new_password: str) -> dict[str, Any]:
        user = self.user_from_token(token, expected_purpose="pwreset")
        if len(new_password) < 8:
            raise AuthError("password must be at least 8 characters")
        user.password_hash = hash_password(new_password)
        self.store.save_user(user)
        return self._public_user(user)

    def delete_account(self, user_id: str) -> dict[str, Any]:
        self.store.require_user(user_id)
        self.store.delete_user(user_id)
        return {"ok": True, "deleted": user_id}

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
