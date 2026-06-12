import { AnalyticsPanel } from "../components/analytics-panel";
import { ArtifactPanel } from "../components/artifact-panel";
import { NotebookBar } from "../components/notebook-bar";
import { NotebookChat } from "../components/notebook-chat";
import { PaperPanel } from "../components/paper-panel";
import { QuizPanel } from "../components/quiz-panel";
import { ReportPanel } from "../components/report-panel";
import { RevisionPanel } from "../components/revision-panel";
import { SolvePanel } from "../components/solve-panel";
import { SourcePanel } from "../components/source-panel";
import { TeachingPanel } from "../components/teaching-panel";
import { VoicePanel } from "../components/voice-panel";
import { NotebookProvider } from "../lib/notebook-context";

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
          <a href="#revise">Revise</a>
          <a href="#progress">Progress</a>
          <a href="#voice">Voice</a>
          <a href="#artifacts">Artifacts</a>
          <a href="#reports">Reports</a>
        </nav>
      </aside>

      <section className="workspace">
        <NotebookProvider>
          <header className="topbar">
            <div>
              <p className="eyebrow">Phase 2 &amp; 3</p>
              <h2>NotebookLM-inspired RAG with teaching, quizzes, papers, revision &amp; analytics</h2>
            </div>
            <NotebookBar />
          </header>

          <div className="grid">
            <SourcePanel />
            <NotebookChat />
            <TeachingPanel />
            <SolvePanel />
            <QuizPanel />
            <PaperPanel />
            <RevisionPanel />
            <AnalyticsPanel />
            <VoicePanel />
            <ArtifactPanel />
            <ReportPanel />
          </div>
        </NotebookProvider>
      </section>
    </main>
  );
}
