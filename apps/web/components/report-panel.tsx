export function ReportPanel() {
  return (
    <section className="panel" id="reports">
      <div className="panelHeader">
        <h3>Evaluation report</h3>
        <span className="badge">Performance</span>
      </div>
      <div className="reportSummary">
        <div className="scoreCircle">
          <strong>--</strong>
          <small>/ --</small>
        </div>
        <p className="reportLevel">Submit a quiz or paper attempt to see your evaluation.</p>
      </div>
      <div className="reportBreakdown">
        <p className="eyebrow">Topic breakdown</p>
        <div className="topicRow"><span>Strong areas</span><span className="strongTag">--</span></div>
        <div className="topicRow"><span>Weak areas</span><span className="weakTag">--</span></div>
      </div>
      <button type="button">View latest report</button>
    </section>
  );
}
