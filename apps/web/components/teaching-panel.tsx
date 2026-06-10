export function TeachingPanel() {
  return (
    <section className="panel wide" id="teach">
      <div className="panelHeader">
        <h3>Teaching whiteboard</h3>
        <span className="badge">Concept walk-through</span>
      </div>
      <div className="conceptDisplay">
        <div className="conceptNav">
          <button type="button">&larr; Previous</button>
          <span className="conceptCounter">1 / 5</span>
          <button type="button">Next &rarr;</button>
        </div>
        <div className="conceptContent">
          <strong className="conceptName">Key concept from your sources</strong>
          <p className="conceptExplanation">
            Explanations derived from your uploaded sources appear here, with citations.
          </p>
        </div>
      </div>
      <button type="button">Start teaching session</button>
    </section>
  );
}
