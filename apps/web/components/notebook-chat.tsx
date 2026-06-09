export function NotebookChat() {
  return (
    <section className="panel wide" id="ask">
      <div className="panelHeader">
        <h3>Ask your notebook</h3>
        <span className="badge">Citations required</span>
      </div>
      <div className="answer">
        <p className="eyebrow">From your sources</p>
        <p>
          Gradient descent updates parameters by moving opposite the gradient of the loss function.
          <sup>[1]</sup>
        </p>
      </div>
      <label className="inputRow">
        <span>Question</span>
        <textarea placeholder="How does gradient descent update parameters?" />
      </label>
      <button type="button">Ask with sources</button>
    </section>
  );
}
