export function SolvePanel() {
  return (
    <section className="panel" id="solve">
      <div className="panelHeader">
        <h3>Verified solve</h3>
        <span className="verified">Verified</span>
      </div>
      <label className="inputRow">
        <span>Problem</span>
        <textarea placeholder="Calculate NPV at 10% for cash flows -100, 60, 60." />
      </label>
      <div className="solveResult">
        <span>Answer</span>
        <strong>4.13</strong>
        <small>formula check</small>
      </div>
      <button type="button">Reveal next step</button>
    </section>
  );
}
