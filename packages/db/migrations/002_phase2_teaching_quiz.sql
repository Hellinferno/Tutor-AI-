CREATE TYPE question_type AS ENUM ('mcq', 'true_false', 'short_answer');
CREATE TYPE attempt_source_type AS ENUM ('quiz', 'paper');
CREATE TYPE difficulty AS ENUM ('easy', 'medium', 'hard');

CREATE TABLE whiteboard_sessions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  current_concept_idx int NOT NULL DEFAULT 0,
  concept_progression jsonb NOT NULL DEFAULT '[]',
  completed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE quizzes (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  title text NOT NULL,
  topic text,
  num_questions int NOT NULL DEFAULT 5,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE quiz_questions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  quiz_id uuid NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
  type question_type NOT NULL,
  question_text text NOT NULL,
  options jsonb,
  correct_answer text NOT NULL,
  points int NOT NULL DEFAULT 1,
  difficulty difficulty NOT NULL DEFAULT 'medium',
  citations jsonb NOT NULL DEFAULT '[]',
  idx int NOT NULL,
  UNIQUE (quiz_id, idx)
);

CREATE TABLE question_papers (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  title text NOT NULL,
  total_marks int NOT NULL,
  duration_minutes int NOT NULL DEFAULT 60,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE paper_sections (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  paper_id uuid NOT NULL REFERENCES question_papers(id) ON DELETE CASCADE,
  title text NOT NULL,
  instructions text,
  idx int NOT NULL,
  UNIQUE (paper_id, idx)
);

CREATE TABLE attempts (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_id uuid NOT NULL,
  source_type attempt_source_type NOT NULL,
  user_id uuid REFERENCES users(id),
  answers jsonb NOT NULL DEFAULT '[]',
  total_score float NOT NULL DEFAULT 0,
  max_score float NOT NULL DEFAULT 0,
  completed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE answer_keys (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_id uuid NOT NULL,
  source_type attempt_source_type NOT NULL,
  answers jsonb NOT NULL DEFAULT '[]',
  verified boolean NOT NULL DEFAULT true,
  verification_method text NOT NULL DEFAULT 'deterministic_source_check',
  generated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE eval_reports (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  attempt_id uuid NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
  total_score float NOT NULL,
  max_score float NOT NULL,
  percentage float NOT NULL,
  per_question jsonb NOT NULL DEFAULT '[]',
  weak_topics jsonb NOT NULL DEFAULT '[]',
  strong_topics jsonb NOT NULL DEFAULT '[]',
  summary text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_quizzes_notebook ON quizzes (notebook_id);
CREATE INDEX idx_papers_notebook ON question_papers (notebook_id);
CREATE INDEX idx_attempts_user ON attempts (user_id, source_type);
CREATE INDEX idx_reports_attempt ON eval_reports (attempt_id);
