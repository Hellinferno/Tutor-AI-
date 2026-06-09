CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE source_kind AS ENUM ('pdf', 'notes', 'slides', 'text', 'other');
CREATE TYPE artifact_type AS ENUM ('summary_notes', 'study_guide', 'planner', 'timetable', 'revision_cards');
CREATE TYPE verify_method AS ENUM ('code_exec', 'symbolic', 'formula', 'self_consistency', 'cross_model', 'unverified');

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  email text UNIQUE,
  subject_domain text DEFAULT 'ai_ds',
  prefs jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE notebooks (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid REFERENCES users(id),
  title text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sources (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  title text NOT NULL,
  kind source_kind NOT NULL DEFAULT 'notes',
  status text NOT NULL DEFAULT 'ready',
  text_sha256 text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE source_chunks (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  chunk_index int NOT NULL,
  text text NOT NULL,
  start_char int NOT NULL,
  end_char int NOT NULL,
  vector_id text NOT NULL,
  UNIQUE (source_id, chunk_index)
);

CREATE TABLE source_guides (
  source_id uuid PRIMARY KEY REFERENCES sources(id) ON DELETE CASCADE,
  summary text NOT NULL,
  key_concepts jsonb NOT NULL DEFAULT '[]',
  suggested_questions jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE questions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  canonical_text text NOT NULL,
  hash text NOT NULL UNIQUE,
  subject text NOT NULL,
  notebook_id uuid REFERENCES notebooks(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE solutions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  question_id uuid NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  steps jsonb NOT NULL,
  answer text NOT NULL,
  verify_method verify_method NOT NULL,
  verified boolean NOT NULL DEFAULT false,
  citations jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE artifacts (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  artifact_type artifact_type NOT NULL,
  title text NOT NULL,
  content_markdown text NOT NULL,
  citations jsonb NOT NULL DEFAULT '[]',
  notion_page_url text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid REFERENCES users(id),
  notebook_id uuid REFERENCES notebooks(id),
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  interactions jsonb NOT NULL DEFAULT '[]'
);

CREATE TABLE revision_cards (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid REFERENCES users(id),
  notebook_id uuid REFERENCES notebooks(id),
  topic text NOT NULL,
  due_date date NOT NULL,
  interval_days int NOT NULL,
  state text NOT NULL DEFAULT 'queued'
);

CREATE INDEX idx_source_chunks_notebook ON source_chunks (notebook_id);
CREATE INDEX idx_questions_hash ON questions (hash);
CREATE INDEX idx_revision_cards_due ON revision_cards (user_id, due_date, state);
