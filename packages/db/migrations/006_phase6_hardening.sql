-- Phase 6: Production hardening & user readiness
--
-- No new tables or columns: Phase 6 hardening is entirely application-layer and
-- reuses the existing schema:
--   * Auth enforcement, CORS, rate limiting, and input-size caps are gateway/runtime concerns.
--   * Account self-service (change/reset password, update profile) updates the existing
--     users row (users.password_hash / subject_domain / prefs from migration 005).
--   * Account deletion cascades across existing tables (notebooks -> sources/chunks/guides/
--     artifacts/sessions/quizzes/papers/imports, plus the user's attempts, revision_cards,
--     sessions, student_profiles/topic_masteries, subscriptions, usage_records).
--
-- Recommended supporting indexes for the cascade and ownership checks (idempotent):
CREATE INDEX IF NOT EXISTS idx_sources_notebook ON sources (notebook_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_notebook ON artifacts (notebook_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts (user_id);
CREATE INDEX IF NOT EXISTS idx_revision_cards_user ON revision_cards (user_id);
