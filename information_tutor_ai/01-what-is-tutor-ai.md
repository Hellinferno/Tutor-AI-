# 01 — What is Tutor‑AI? (for everyone) 🟢

*No technical knowledge needed. This explains what the product does and why it's built the way
it is.*

---

## The problem it solves

Students studying AI, data science, analytics, and finance have a lot of material — lecture
notes, PDFs, slides — and a lot of questions. Generic AI chatbots have two problems:

1. **They make things up** ("hallucinate"). They sound confident even when wrong.
2. **They don't know *your* material.** They answer from the internet, not from your professor's
   notes.

Tutor‑AI is designed to fix both.

---

## What it actually does

Think of it as a **smart study notebook**. Here is the experience:

### 1. You create a "notebook" and upload your sources
A notebook is just a labelled container — e.g. "Machine Learning 101." You paste or upload your
notes, slides, or text into it.

### 2. It reads each source and makes a "source guide"
For every source you add, it writes a short summary, pulls out the key concepts, and suggests
questions you could ask. Like a friend skimming your notes and saying "here's what matters."

### 3. You ask questions — it answers *only from your sources*
This is the important part. When you ask a question:
- It finds the most relevant passages **in your uploaded material**.
- It answers using those passages and **shows you exactly where each fact came from** (a
  "citation" — the source title and location).
- If your sources **don't** contain enough to answer, it **says so honestly** instead of
  guessing. (We call this "low‑confidence rejection.")

> 🟢 **Why this matters:** You can trust the answer because you can check the source. The app
> would rather say "I don't have enough in your notes for this" than invent an answer.

### 4. It solves problems — and *checks its own work*
For math, finance, and coding questions, Tutor‑AI doesn't just produce an answer — it
**verifies** it:
- **Math** (e.g. `2 + 2 * 3`) is actually calculated, not guessed.
- **Finance** (e.g. "Net Present Value at 10% for these cash flows") is computed with the real
  formula.
- **Code** (e.g. a small Python snippet) is **actually run** in a safe, locked‑down mini‑computer
  ("sandbox") and the real output becomes the answer.

If it can't verify an answer objectively, it tells you it's **unverified**. The project has a
strict rule: the rate of answers *falsely claimed as verified* must be **zero**.

### 5. It builds study materials for you
From your notebook it can generate:
- **Summary notes**
- **Study guides**
- **Study planners** and **timetables**
- **Revision cards** (with a built‑in review schedule)

And it can **export** these to **Notion** (a popular note‑taking app).

---

## A day‑in‑the‑life example

> Priya uploads her "Valuation" lecture notes. Tutor‑AI summarises them and lists key concepts
> like *net present value* and *discount rate*. She asks, *"What's the NPV cash‑flow formula?"* —
> it answers using her notes and cites the exact passage. Then she types *"Calculate NPV at 10%
> for cash flows ‑100, 60, 60"* and it returns **4.13**, marked **verified** because it ran the
> real formula. Finally she clicks "generate study guide" and exports it to her Notion workspace
> for revision week.

---

## What's built right now (and what isn't)

✅ **Built and working today** (Phase 0 + Phase 1): notebooks, source upload, source guides,
grounded answers with citations, honest refusal, verified math/finance/code solving, study
artifacts, Notion export, and durable saving of your data.

🚧 **Planned for later** (not built yet): an interactive teaching engine with a whiteboard,
auto‑generated quizzes and exam papers, long‑term memory and spaced‑repetition revision,
progress analytics, and voice input/output.

For the precise, honest breakdown see [11-current-status.md](11-current-status.md).

---

## How it's put together (the 30‑second version)

The product is split into a few cooperating parts:

- A **website** (what you see and click).
- A **gateway** that receives requests from the website.
- A **RAG engine** that finds relevant passages and writes grounded answers. ("RAG" =
  *Retrieval‑Augmented Generation* — see the [glossary](12-glossary.md).)
- A **solver** that computes and verifies answers.
- A **store** that remembers your notebooks, sources, and answers.

The developer‑level picture is in [02-architecture.md](02-architecture.md).
