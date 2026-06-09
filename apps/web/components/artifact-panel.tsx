const artifacts = ["Summary", "Study guide", "Planner", "Timetable", "Revision"];

export function ArtifactPanel() {
  return (
    <section className="panel wide" id="artifacts">
      <div className="panelHeader">
        <h3>Study artifacts</h3>
        <span className="badge">Notion export</span>
      </div>
      <div className="artifactButtons">
        {artifacts.map((artifact) => (
          <button type="button" key={artifact}>
            {artifact}
          </button>
        ))}
      </div>
      <div className="notionBox">
        <strong>Export target</strong>
        <p>Private Notion page by default. Add a parent page or database later.</p>
        <button type="button">Export to Notion</button>
      </div>
    </section>
  );
}
