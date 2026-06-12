-- Phase 3: Spaced repetition, student mastery, analytics, voice

-- Add columns to revision_cards from Phase 0 stub
ALTER TABLE revision_cards ADD COLUMN IF NOT EXISTS easiness_factor float NOT NULL DEFAULT 2.5;
ALTER TABLE revision_cards ADD COLUMN IF NOT EXISTS correct_streak int NOT NULL DEFAULT 0;
ALTER TABLE revision_cards ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'manual';

-- Add kind column to sessions from Phase 0 stub
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'study';

-- Student profiles (one per user+notebook)
CREATE TABLE IF NOT EXISTS student_profiles (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid REFERENCES users(id),
  notebook_id uuid REFERENCES notebooks(id),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, notebook_id)
);

-- Topic mastery records per student profile
CREATE TABLE IF NOT EXISTS topic_masteries (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_profile_id uuid NOT NULL REFERENCES student_profiles(id) ON DELETE CASCADE,
  topic text NOT NULL,
  score float NOT NULL,
  attempt_count int NOT NULL DEFAULT 0,
  last_attempt_date timestamptz,
  UNIQUE (student_profile_id, topic)
);

-- Indexes for Phase 3 queries
CREATE INDEX IF NOT EXISTS idx_masteries_profile ON topic_masteries (student_profile_id);
CREATE INDEX IF NOT EXISTS idx_revision_cards_state ON revision_cards (user_id, state);
