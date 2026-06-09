import { ArtifactPanel } from "../components/artifact-panel";
import { NotebookChat } from "../components/notebook-chat";
import { SolvePanel } from "../components/solve-panel";
import { SourcePanel } from "../components/source-panel";

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
          <a href="#solve">Solve</a>
          <a href="#artifacts">Artifacts</a>
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Phase 1</p>
            <h2>NotebookLM-inspired RAG with verified solving</h2>
          </div>
          <span className="status">Local gateway: /v1</span>
        </header>

        <div className="grid">
          <SourcePanel />
          <NotebookChat />
          <SolvePanel />
          <ArtifactPanel />
        </div>
      </section>
    </main>
  );
}
