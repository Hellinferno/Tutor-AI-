-- Phase 5: Production readiness — authentication, authorization, observability

-- The users table is defined in 001 (id, email, subject_domain, prefs, created_at);
-- Phase 5 adds the password hash needed for first-party email/password auth.
-- (PBKDF2-HMAC-SHA256, stored as algo$iterations$salt$hash.)
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash text;

-- Helpful lookups for login and ownership checks.
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_notebooks_user ON notebooks (user_id);

-- JWTs are stateless (HS256, signed with STUDYLAB_JWT_SECRET), so no session
-- table is required. Quota enforcement reuses the Phase 4 subscriptions +
-- usage_records tables; observability metrics are in-process counters exposed at
-- GET /metrics and are not persisted.
