-- Phase 9: Discussions, instructor feedback, and notifications
--
-- Three independent stores that turn the multi-user product into a connected one:
--
--   * comments              — threaded discussion comments on a notebook
--   * submission_feedback   — instructor feedback (optionally with a grade override)
--                             written against an assignment_submissions row
--   * notifications         — best-effort inbox rows dropped by share / enroll /
--                             assign / submit / grade / comment-post events

CREATE TABLE IF NOT EXISTS comments (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  author_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body text NOT NULL,
  parent_id uuid REFERENCES comments(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS submission_feedback (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  submission_id uuid NOT NULL REFERENCES assignment_submissions(id) ON DELETE CASCADE,
  instructor_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  feedback text NOT NULL,
  override_score numeric,          -- if set, replaces the auto-graded total when computing %
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind text NOT NULL,              -- notebook_shared | assignment_created | submission_received | submission_graded | comment_posted | class_enrolled
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  read_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_comments_notebook ON comments (notebook_id, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_submission ON submission_feedback (submission_id);
CREATE INDEX IF NOT EXISTS idx_notifs_user ON notifications (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notifs_unread ON notifications (user_id) WHERE read_at IS NULL;
