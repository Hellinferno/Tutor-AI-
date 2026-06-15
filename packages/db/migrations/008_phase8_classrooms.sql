-- Phase 8: Classrooms, assignments, class analytics
--
-- An instructor (role='instructor' or 'admin') owns a class. Students enroll
-- via a short join code. An assignment points at an existing quiz or question
-- paper (must be in the instructor's notebook). Students submit through the
-- standard eval pipeline; the resulting Attempt is linked back to the
-- assignment via assignment_submissions so the instructor can see class-wide
-- results and per-assignment analytics.

CREATE TABLE IF NOT EXISTS classes (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  instructor_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  code text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS class_enrollments (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  class_id uuid NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  joined_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (class_id, student_id)
);

CREATE TABLE IF NOT EXISTS assignments (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  class_id uuid NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
  kind text NOT NULL,                   -- 'quiz' | 'paper'
  source_id uuid NOT NULL,              -- references quizzes(id) or question_papers(id) depending on kind
  title text NOT NULL,
  due_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assignment_submissions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  assignment_id uuid NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  attempt_id uuid NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
  submitted_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_classes_instructor ON classes (instructor_id);
CREATE INDEX IF NOT EXISTS idx_enroll_class ON class_enrollments (class_id);
CREATE INDEX IF NOT EXISTS idx_enroll_student ON class_enrollments (student_id);
CREATE INDEX IF NOT EXISTS idx_assignments_class ON assignments (class_id);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON assignment_submissions (assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_student ON assignment_submissions (student_id);
