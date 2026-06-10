const types = ["Multiple choice", "True/False", "Short answer"];

export function QuizPanel() {
  return (
    <section className="panel" id="quiz">
      <div className="panelHeader">
        <h3>Quiz generator</h3>
        <span className="badge">From your sources</span>
      </div>
      <div className="quizGen">
        <button type="button">Generate quiz</button>
        {types.map((type) => (
          <button type="button" className="typeBtn" key={type}>
            {type}
          </button>
        ))}
      </div>
      <div className="quizQuestion">
        <p className="eyebrow">Question</p>
        <p>Quiz questions based on your notebook sources appear here.</p>
        <div className="quizOptions">
          <label><input type="radio" name="q" disabled /> Option A</label>
          <label><input type="radio" name="q" disabled /> Option B</label>
          <label><input type="radio" name="q" disabled /> Option C</label>
        </div>
      </div>
      <button type="button" className="submitBtn">Submit answer</button>
    </section>
  );
}
