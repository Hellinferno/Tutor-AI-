-- Phase 4: Source connectors, multi-agent teaching, pricing & economics

-- Imported sources (website / youtube / audio / google_doc / google_slides).
-- The actual content lands in `sources`/`source_chunks` via the normal ingest path;
-- this table records the connector provenance, metadata, and any import warnings.
CREATE TABLE IF NOT EXISTS source_imports (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  connector_type text NOT NULL,
  title text NOT NULL,
  status text NOT NULL DEFAULT 'ready',
  metadata jsonb NOT NULL DEFAULT '{}',
  warnings jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Multi-agent teaching sessions (explainer / verifier / coach turns per concept).
CREATE TABLE IF NOT EXISTS multi_agent_teaching_sessions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  current_concept_idx int NOT NULL DEFAULT 0,
  concepts jsonb NOT NULL,
  agent_turns jsonb NOT NULL,
  completed boolean NOT NULL DEFAULT false
);

-- Subscriptions: one current plan per user (latest row wins).
CREATE TABLE IF NOT EXISTS subscriptions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tier text NOT NULL DEFAULT 'free',
  status text NOT NULL DEFAULT 'active',
  billing_period text NOT NULL,         -- YYYY-MM
  provider text NOT NULL DEFAULT 'mock',
  external_id text,                      -- billing provider subscription/session id
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Usage metering, one row per metered action.
CREATE TABLE IF NOT EXISTS usage_records (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  action text NOT NULL,                  -- ask / solve / quiz / paper / artifact / source_import / teaching
  billing_period text NOT NULL,         -- YYYY-MM
  quantity int NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for Phase 4 queries
CREATE INDEX IF NOT EXISTS idx_source_imports_notebook ON source_imports (notebook_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_notebook ON multi_agent_teaching_sessions (notebook_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_user_period ON usage_records (user_id, billing_period);
