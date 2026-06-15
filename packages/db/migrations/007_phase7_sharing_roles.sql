-- Phase 7: Collaboration, sharing & roles

-- Roles on users (student | instructor | admin). Admin is granted at registration
-- to emails in STUDYLAB_ADMIN_EMAILS; instructor is reserved for future class flows.
ALTER TABLE users ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'student';

-- Notebook sharing: one row per (notebook, recipient). A viewer share grants
-- read / ask / generate; an editor share also grants writes (add/modify sources).
CREATE TABLE IF NOT EXISTS notebook_shares (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  notebook_id uuid NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  shared_with_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  shared_with_email text NOT NULL,
  role text NOT NULL DEFAULT 'viewer',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (notebook_id, shared_with_id)
);

CREATE INDEX IF NOT EXISTS idx_shares_notebook ON notebook_shares (notebook_id);
CREATE INDEX IF NOT EXISTS idx_shares_user ON notebook_shares (shared_with_id);
