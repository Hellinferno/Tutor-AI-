export function PaperPanel() {
  return (
    <section className="panel wide" id="papers">
      <div className="panelHeader">
        <h3>Question paper</h3>
        <span className="badge">Exam mode</span>
      </div>
      <div className="paperHeader">
        <span><strong>Duration:</strong> 60 min</span>
        <span><strong>Sections:</strong> 3</span>
        <span><strong>Total marks:</strong> 30</span>
      </div>
      <div className="paperSection">
        <p className="eyebrow">Section 1: Multiple choice</p>
        <p>Answer all questions. Each carries 2 marks.</p>
      </div>
      <button type="button">Generate question paper</button>
      <button type="button" className="secondary">View answer key</button>
    </section>
  );
}
