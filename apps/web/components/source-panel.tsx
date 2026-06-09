export function SourcePanel() {
  return (
    <section className="panel" id="sources">
      <div className="panelHeader">
        <h3>Sources</h3>
        <button type="button" aria-label="Upload source">+</button>
      </div>
      <div className="sourceItem">
        <strong>Gradient Descent Notes</strong>
        <span>Ready · 4 chunks · source guide generated</span>
      </div>
      <div className="guide">
        <p className="eyebrow">Source guide</p>
        <p>Key ideas, terms, and suggested questions appear here after upload.</p>
      </div>
    </section>
  );
}
