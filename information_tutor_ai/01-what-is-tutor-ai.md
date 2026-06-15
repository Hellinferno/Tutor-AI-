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

### 10. It's ready for real people to use
The latest layer (Phase 6) is about being genuinely usable and safe in the real world:
- **Manage your own account** — change your password, reset it if you forget (via a one‑time token),
  switch your subject focus, or **delete your account and all its data** in one click.
- **Start in seconds** — a "Load sample" button creates a ready‑made notebook with example notes so
  you can try teaching, quizzes, and solving immediately.
- **Safety rails** — the service protects itself with request rate limits, limits on how much text a
  single source can contain, and proper cross‑site protections so the website and server work
  together securely. When secure mode is on, you can only ever see your own data.

> 🟢 **Safe to try:** the login/usage protections ship **switched off by default** so anyone can run
> the app with no setup; flipping one environment switch turns on real login enforcement, usage
> limits, and rate limiting for production.

### 11. You can study together
Phase 7 makes StudyLab multi-user:
- **Share a notebook** with a classmate by email, as a **viewer** (can read, ask questions, and
  generate quizzes/notes) or an **editor** (can also add and change sources).
- **"Shared with me"** lists every notebook other people have shared with you — open one in a click.
- **Roles** — accounts can be a student, an instructor, or an admin; admins get a users overview and
  the system‑health metrics. (Admins are set by the operator.)

> 🟢 **Privacy is preserved:** you can only open a notebook you own or that was explicitly shared with
> you; a viewer can't modify someone else's sources.

### 12. Instructors can run classes
Phase 8 turns the *instructor* role into a real teaching surface:
- **Create a class** as an instructor — you get a short **join code** (like `ABC123`) to share with
  your students.
- **Students join** with the code in one click; the instructor sees the **roster**.
- **Assign a quiz or paper** to the class from your own notebook, optionally with a **due date**.
- **Students see "My assignments"** across every class they've joined, with due dates.
- When a student **submits**, Tutor‑AI scores it through the same eval engine that grades practice
  quizzes — and the instructor sees every submission and a **class‑wide analytics view**:
  completion rate per assignment, average score, and the topics the class is weakest on.
- An **admin promotes** ordinary users to instructors when they're ready to teach.

> 🟢 **Why it matters:** students get a single place to see what they owe; instructors get an
> auto‑graded class with weak‑topic insights without leaving Tutor‑AI for a spreadsheet.

### 13. Discussion, feedback, and a notifications inbox
The newest layer (Phase 9) makes the multi‑user product *feel* connected:
- **Threaded discussion comments** on any notebook — everyone the notebook is shared with (and the
  owner) can post, ask follow‑up questions, or trade study notes in one place.
- **Instructor feedback on submissions** — beside the auto‑grade, the instructor can write a
  personal note and (optionally) **override the score**. The override wins in submission listings
  and class analytics, so the instructor's grade is always the final one.
- **Notifications inbox** — when someone shares a notebook with you, joins your class, posts an
  assignment, submits one of yours, leaves you feedback, or comments on a notebook you can see,
  a row drops into your inbox. You can mark items read one‑at‑a‑time or "mark all read."

> 🟢 **Why it matters:** sharing a notebook was already possible; commenting on it makes it a
> conversation. Auto‑grading was already there; instructor feedback makes the grade *yours*.
> And the inbox means you stop having to refresh classroom + sharing pages just to see what
> changed.

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

✅ **Built and working today** (Phase 0 → Phase 9): notebooks, source upload, source guides, grounded
answers with citations, honest refusal, verified math/finance/code solving, study artifacts, Notion
export, durable saving of your data, the teaching whiteboard, quizzes, question papers, verified
answer keys, auto‑graded reports, spaced‑repetition revision, a per‑topic mastery model, progress
analytics, voice input/output, the website / YouTube / audio / Google Docs connectors, multi‑agent
teaching, Free/Scholar/Pro plans with usage metering, real accounts (login) with per‑user privacy and
a system‑health dashboard, full account self‑service (change/reset password, delete account),
one‑click sample onboarding, production safety rails (rate limits, input caps, CORS), notebook
sharing (viewer/editor) with a "shared with me" view, student/instructor/admin roles, classrooms
with join codes, assignments and due dates, submission tracking, class‑wide analytics, **plus
threaded notebook discussions, instructor feedback on submissions (with optional grade override),
and a notifications inbox** — all driven from a working, responsive interactive website.

🚧 **Planned for later**: a **native mobile app** (the website is already responsive),
**horizontal‑scaling** infrastructure, **social login (OAuth/SSO)**, and wiring an **email provider**
to deliver password‑reset links. Real external services — Postgres, Qdrant, embeddings, OCR, the
voice provider, connector fetch‑workers, and Stripe billing — are wired as env‑gated adapters you can
switch on with a key.

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
