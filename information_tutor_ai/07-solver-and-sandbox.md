# 07 — Verified Solver & Code Sandbox 🟢🔵

How Tutor‑AI produces answers it can **prove**, and how it runs code safely.

---

## 🟢 The plain‑English version

A normal chatbot *guesses* answers. Tutor‑AI **checks** them. For three kinds of problems it uses
a real checker, and only then calls the answer "verified":

- **Math** — it actually calculates `2 + 2 * 3 = 8`.
- **Finance** — it computes Net Present Value with the real formula.
- **Code** — it *runs* your Python snippet inside a locked‑down mini‑computer and uses the real
  output.

If it can't check an answer objectively, it labels it **unverified** and says so. The project's
hard rule: **never mark a wrong answer as verified** (target false‑verified rate = 0).

---

## 🔵 Solver routing

Code: [solver.py](../packages/studylab_core/studylab_core/solver.py).

`SolverEngine.solve(question, subject, notebook_id)`:

1. **Cache** — hash the normalised question; return the cached solution if seen before
   (`from_cache: true`).
2. **Optional grounding** — if a `notebook_id` is given, attach retrieval citations.
3. **Route** to the first objective method that applies:

   | Order | Method | Trigger | Verified? |
   |---|---|---|---|
   | 1 | `code_exec` | an extractable Python snippet (fenced block, or input that parses as code) | ✅ if it runs cleanly |
   | 2 | `formula` | NPV / "net present value" with a rate and ≥2 cash flows | ✅ |
   | 3 | `symbolic` | a safe arithmetic expression (`+ - * / ** ()`) | ✅ |
   | — | `unverified` | none of the above (e.g. conceptual) | ❌ honestly unverified |

   > Code is checked **first** on purpose: a snippet like `print(6*7)` must *run* rather than be
   > scraped for stray numbers by the arithmetic path.

4. **Store** the solution with three reveal‑ready steps (normalise → compute → verify). The first
   step is revealed; the rest unlock via `reveal`.

### Symbolic & finance details
- `try_symbolic` parses the largest numeric expression with Python's `ast` in a **whitelisted**
  evaluator (only `+ - * / ** ()` and unary minus) — no arbitrary code, no names.
- `try_finance_formula` parses the rate and cash flows and computes
  `Σ cashflow_t / (1+r)^t`.

---

## 🔵 The code sandbox

Code: [sandbox.py](../packages/studylab_core/studylab_core/sandbox.py).

Running user code is dangerous, so execution is guarded in two layers:

### Layer 1 — static allowlist (before anything runs)
`validate_code` parses the snippet to an AST and **rejects** it unless it's safe:
- **Imports** must be from a small allowlist (`math`, `statistics`, `random`, `decimal`,
  `fractions`, `itertools`, `functools`, `collections`, `json`, `re`, `datetime`, …). Anything
  like `os`, `sys`, `socket`, `subprocess`, `requests`, `pathlib` is rejected.
- **Forbidden builtins** are blocked: `open`, `exec`, `eval`, `compile`, `input`, `__import__`,
  `globals`, `getattr`/`setattr`, `breakpoint`, …
- **Dunder attribute access** (`__class__`, `__globals__`, …) is blocked to prevent escapes.

### Layer 2 — isolated subprocess (how it runs)
`run_code` launches `python -I -S -c <code>`:
- `-I` = **isolated mode** (ignores environment variables and user site‑packages).
- `-S` = no site customisation.
- A **restricted environment** (only the few vars needed to launch the interpreter; secrets/API
  keys are stripped).
- A **timeout** (default 5s) to stop infinite loops.
- **stdout is captured** as the verified answer; a non‑zero exit or rejection returns
  `unverified` with the reason.

> 🟢 **Plain English:** the code runs in a bare, disconnected sandbox with no internet, no files,
> no secrets, and a time limit. If it tries anything unsafe, it's blocked *before* it runs.

### Worked examples (from the test suite)
| Input | Result |
|---|---|
| ```` ```python\nprint(6 * 7)\n``` ```` | `verified`, `code_exec`, answer `42` |
| ```` ```python\nimport socket\nprint(socket.gethostname())\n``` ```` | `unverified` (import blocked) |
| `open('/etc/passwd')` | rejected by `validate_code` |

---

## OCR path (image input)
Code: [ocr.py](../packages/studylab_core/studylab_core/ocr.py). When `input_type: "image"`, the
content goes through an OCR adapter to extract text, which then enters the same solver routing. The
current adapter is a local placeholder (decodes provided text) with a clean seam for a real OCR
service — see [11-current-status.md](11-current-status.md).
