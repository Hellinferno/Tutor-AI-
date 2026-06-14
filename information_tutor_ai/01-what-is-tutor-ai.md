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

### 6. It teaches, quizzes, and tests you
Once you have sources in a notebook, Tutor‑AI can:
- **Teach** the material as a step‑by‑step "whiteboard" walk‑through of the key concepts — each
  explanation drawn from (and cited back to) your own notes.
- **Generate quizzes** — multiple‑choice, true/false, and short‑answer — either from your sources
  or from a topic you name.
- **Generate full question papers** with sections, marks, and a time limit.
- **Grade your attempts automatically** and give you a **report**: your score, which topics you got
  right, which you missed, and a short summary.

> 🟢 **Same honesty rule:** the questions and the answer keys are built **from your sources** (not
> invented), and every answer key is **checked** before it's trusted — so practice doesn't teach you
> something wrong.

### 7. It remembers your progress and helps you revise
As you use it, Tutor‑AI builds a picture of how you're doing:
- **Spaced‑repetition revision cards** — it turns your topics into flashcards and schedules them so
  you review each one just before you'd forget it (the well‑known "SM‑2" method).
- **A student model** — by looking at your quiz/paper results, it works out which topics you've
  **mastered** and which are **weak**.
- **Progress analytics** — a simple dashboard of your score trend over attempts and an overall
  summary.
- **Voice in and out** — speak a question or have an answer read aloud (uses a real speech provider
  when configured, a safe stand‑in otherwise).

> 🟢 **The website is a real, working app.** Every panel — sources, ask, teach, solve, quiz, papers,
> artifacts, reports, revision, analytics — is connected to the live backend. It is no longer a
> visual mockup.

### 8. It pulls in more kinds of sources, teaches with a team of agents, and has real plans
The latest layer (Phase 4) adds:
- **More source connectors** — bring in a **website**, a **YouTube** video, an **audio** recording,
  or a **Google Doc / Slides**. The text/transcript is imported, then chunked and cited exactly like
  an upload (so answers stay grounded and checkable).
- **Multi‑agent teaching** — instead of one explanation, a small *team* walks you through each
  concept: an **explainer** teaches it, a **grounding‑verifier** checks how well it's backed by your
  sources, and a **practice‑coach** gives you the next move. Every turn is still cited.
- **Plans & usage** — Free, Scholar, and Pro plans with clear monthly usage allowances, a live
  meter of what you've used, and one‑click plan switching. (Real card payments turn on when a
  payment key is configured; until then it runs in a safe mock mode.)

> 🟢 **Mobile:** the website is fully **responsive** — it reshapes to fit a phone screen — so you can
> study on the go. (A separate native mobile app is still future work.)

### 9. It has real accounts and shows its own health
The production‑readiness layer (Phase 5) adds:
- **Accounts** — sign up and sign in with an email and password (passwords are stored only as a
  salted, one‑way "hash", never as plain text). Your notebooks, usage, and plan belong to **your**
  account.
- **Private by default** — when the server is run in its secure mode, every request must carry your
  login token, and you can only open your own notebooks.
- **Real usage limits** — in secure mode, going over your plan's monthly allowance is actually
  blocked (with a clear "upgrade your plan" message) rather than just counted.
- **A health dashboard** — a simple panel shows how the system is doing: how often it correctly
  refused to answer, how often answers were verified, how fast solving is, and the cache hit rate.

> 🟢 **Safe to try:** these protections ship **switched off by default** so anyone can run the app
> with no setup; flipping one environment switch turns on real login enforcement and usage limits.

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

✅ **Built and working today** (Phase 0 → Phase 5): notebooks, source upload, source guides, grounded
answers with citations, honest refusal, verified math/finance/code solving, study artifacts, Notion
export, durable saving of your data, the teaching whiteboard, quizzes, question papers, verified
answer keys, auto‑graded reports, spaced‑repetition revision, a per‑topic mastery model, progress
analytics, voice input/output, the website / YouTube / audio / Google Docs connectors, multi‑agent
teaching, Free/Scholar/Pro plans with usage metering, **plus real accounts (login), per‑user privacy,
enforceable usage limits, and a system‑health dashboard** — all driven from a working, responsive
interactive website.

🚧 **Planned for later**: a **native mobile app** (the website is already responsive),
**horizontal‑scaling** infrastructure, and **social login (OAuth/SSO) + password reset**. Real
external services — Postgres, Qdrant, embeddings, OCR, the voice provider, connector fetch‑workers,
and Stripe billing — are wired as env‑gated adapters you can switch on with a key.

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
