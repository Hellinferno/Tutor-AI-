import { ArtifactPanel } from "../components/artifact-panel";
import { NotebookChat } from "../components/notebook-chat";
import { PaperPanel } from "../components/paper-panel";
import { QuizPanel } from "../components/quiz-panel";
import { ReportPanel } from "../components/report-panel";
import { SolvePanel } from "../components/solve-panel";
import { SourcePanel } from "../components/source-panel";
import { TeachingPanel } from "../components/teaching-panel";

export default function Page() {
  return (
    <main className="shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">StudyLab</p>
          <h1>Source notebook</h1>
        </div>
        <nav className="nav">
          <a href="#sources">Sources</a>
          <a href="#ask">Ask</a>
          <a href="#teach">Teach</a>
          <a href="#solve">Solve</a>
          <a href="#quiz">Quiz</a>
          <a href="#papers">Papers</a>
          <a href="#artifacts">Artifacts</a>
          <a href="#reports">Reports</a>
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Phase 2</p>
            <h2>NotebookLM-inspired RAG with teaching, quizzes & papers</h2>
          </div>
          <span className="status">Local gateway: /v1</span>
        </header>

        <div className="grid">
          <SourcePanel />
          <NotebookChat />
          <TeachingPanel />
          <SolvePanel />
          <QuizPanel />
          <PaperPanel />
          <ArtifactPanel />
          <ReportPanel />
        </div>
      </section>
    </main>
  );
}
