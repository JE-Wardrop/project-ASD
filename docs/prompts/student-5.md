# Prompt Engineering and AI Context Management — Student 5

**Feature:** Transaction Management
**Author:** Gia Tran (student-5)
**Release:** 0

This document records how AI-assisted software engineering was used while
building the Transaction Management microservices, as required by the unit's
AI usage policy (§4.4, §4.6). It covers the prompts used, what was returned,
what was changed before use, and how each output was verified.

The AI tool used for development assistance was Claude. The application's own
AI feature uses Ollama with Qwen, and is documented separately in the
architecture section of the report.

---

## 1. Context management strategy

Poor context produces confident but wrong answers, so context was managed
deliberately rather than by pasting fragments into a chat window.

**What was supplied to the assistant**

| Context | Why |
|---|---|
| `ASD_2026_Project_Specifications.pdf` | So suggestions were checked against the actual rubric, not general best practice |
| Release 0 Brief and marking criteria | To keep work aligned to what is assessed |
| Signed Project Group Registration Form | So the code matched the API list approved by the tutor |
| Direct read access to the repository | So the assistant read the real files instead of being told about them |
| The unit's lab template structure | So the submission matched what the marker expects to see |

**What was deliberately withheld**

- Credentials and tokens. A GitHub personal access token was found embedded in
  the team's registration form and was revoked; nothing of that kind was ever
  pasted into a prompt.
- Teammates' source files were read but never rewritten by the assistant
  without their agreement.

**How context was kept accurate**

Giving the assistant read access to the repository proved more reliable than
describing the code. Several times a described state and the real state
differed — for example a `prompts/` folder that was assumed to exist but did
not — and only a direct file read caught it.

---

## 2. Prompt log

### 2.1 Database schema design

**Intent:** design the `transactions` table.

**Prompt:** *"For a banking transaction table supporting deposits, withdrawals
and transfers, should sender and receiver account columns be nullable? What
constraints should the schema enforce itself?"*

**Response:** Both account columns must be nullable, because a deposit has no
sender and a withdrawal has no receiver. A table-level `CHECK` can enforce the
correct combination per transaction type.

**Changed before use:** The suggested constraint was extended to also reject
transfers where sender and receiver are the same account.

**Verification:** Three deliberate violations were inserted — a `DEPOSIT`
carrying a sender, a negative amount, and a self-transfer. All three were
rejected by SQLite. These became unit tests.

---

### 2.2 Rejecting an AI-proposed architecture

**Intent:** decide where AI-Mode should live.

**Prompt:** *"Where should the Ollama client live — in each backend, or in a
shared AI service?"*

**Response:** A separate `ai-service` container in front of Ollama, so that
MCP and RAG could be added behind the same interface in Release 1.

**Changed before use:** **Rejected.** The specification defines the request
workflow as *Frontend → Backend/API → Ollama → LLM* — four hops, not five.
The unit's lab template also places the LLM client inside the backend. The
suggestion was reasonable engineering but did not match the specification,
so the extra service was deleted and the client moved into
`backend/services/llm_client.py`.

**Verification:** Compared against §6.2.1 of the specification and against the
lab template; confirmed no service in the repository calls an intermediate
AI service.

> This entry is kept deliberately. Assistant output is a proposal, not an
> instruction, and the specification outranks it.

---

### 2.3 Cross-service failure handling

**Intent:** decide what the Transaction backend should do when the Account
service cannot be reached.

**Prompt:** *"My backend calls another team member's Account service. What
should happen when that service is unreachable, versus when it replies that
the account does not exist?"*

**Response:** These are different conditions and must not share a return
value. "Does not exist" is a business answer (400); "cannot be reached" is an
infrastructure failure (503).

**Changed before use:** Adopted as designed, with a development flag
(`REQUIRE_ACCOUNTS`) so the feature could be built before the Account service
existed.

**Verification:** Integration tests with a stub Account service confirm that a
withdrawal beyond the balance is refused and the balance is unchanged.

---

### 2.4 AI-Mode returning unusable output

**Intent:** fix a money-flow summary that described JSON instead of money.

**Observed failure:** The model replied *"It looks like you've provided a JSON
object containing transaction records…"* and then listed field names.

**Prompt:** *"The model is describing the data structure instead of
summarising the customer's money. The transactions are passed in as JSON. How
should this be fixed?"*

**Response:** Three causes — the model was too small, raw JSON invites the
model to describe JSON, and asking a small model to total fifty records
invites hallucinated figures. Compute the totals in Python and pass a short
plain-text summary; the model then only has to write the sentence.

**Changed before use:** Adopted, and extended: the prompt files were rewritten
to remove all schema vocabulary, to forbid opening preambles, and to include
one worked example of an acceptable answer.

**Verification:** `_summarise()` output was checked by hand against the seed
data — money in $2,500.00, money out $650.00, with the `FAILED` $3,200.00
transaction correctly excluded.

**Design decision recorded:** financial figures are computed deterministically
in the backend. The LLM is responsible for wording, never for arithmetic.

---

### 2.5 Application prompt files

The AI-Mode prompts are versioned as files under
`student-5/backend/prompts/` so they can be revised without changing Python.

| File | Purpose |
|---|---|
| `transaction_system_prompt.txt` | Standing rules: use only supplied figures, never invent amounts, no markdown, no data-format vocabulary, no financial advice |
| `explain_transaction_prompt.txt` | Explains why a transaction is pending, failed or cancelled, using the stored description as the reason |
| `analyse_money_flow_prompt.txt` | Three-sentence money-flow summary from pre-computed totals |

**Iteration:** the first system prompt was too long and mostly ignored by
`qwen2.5:0.5b`. It was shortened, the strongest constraint was moved to the
front, and a worked example was added to each task prompt. Small models follow
a demonstrated example far better than a described rule.

---

### 2.6 Debugging a silent frontend

**Intent:** find why the Explain button produced no visible result.

**Prompt:** *"The button fires, the server logs show the request, but nothing
appears on the page."*

**Response:** Two separate problems. The AI call was failing because
`OLLAMA_BASE_URL` defaulted to `host.docker.internal`, which only resolves
inside a container. And HTMX ignores responses that are not 2xx, so the error
message the backend returned was received but never rendered.

**Changed before use:** The default was changed to `localhost` with Compose
supplying the container value — matching how `DB_URL` and `ACCOUNTS_URL`
already worked. Error responses for HTMX fragments now return 200 with the
alert as the body.

**Verification:** Server log showed `POST /transactions/52/ai/explain 500`
before the fix and `200` after; the alert now renders in the page.

---

### 2.7 Test suite design

**Intent:** write tests that run in CI without the services being up.

**Prompt:** *"How do I test a backend that reaches its database over HTTP,
without starting containers in CI?"*

**Response:** Separate pure functions (unit) from wired components
(integration). For integration, redirect the database client at the database
service's Flask test client instead of real HTTP, and substitute an in-memory
Account service.

**Changed before use:** Adopted. The endpoint collector was additionally
restricted to GET requests only — the first version issued POSTs, which in
this feature would have created real transactions on every run.

**Verification:** 65 tests pass locally and in GitHub Actions with no services
running.

---

### 2.8 Reviewing the CI workflow

**Intent:** check `student-5.yml` before pushing.

**Prompt:** *"Review this workflow against the specification. Do not change
the code, just tell me what is wrong."*

**Response:** Five issues — paths left over from the lab
(`enrolment-app-open-ai`), `working-directory` applied to only one step,
smoke checks calling `/` on services that only expose `/health`, building the
whole team's compose file so another student's broken Dockerfile would fail
this workflow, and no pytest step despite 65 tests existing.

**Changed before use:** All five corrected. Builds were narrowed to
`student5-db`, `student5-backend`, `student5-frontend` as §7.3 requires.

**Verification:** `docker compose config -q` and a local build passed before
pushing; the workflow then ran green in GitHub Actions.

---

### 2.9 Agentic loop — shared, not personal

**Intent:** the team's agentic loop was hardcoded to one student's feature.

**Prompt:** *"This shared loop only reviews Card Management. How can every
student run it against their own services without forking it?"*

**Response:** Move the per-student values into a target registry selected by a
`REVIEW_TARGET` environment variable, and make the collectors check what the
specification requires of every student — an owned schema, at least ten seeded
records, three containerised tiers — rather than feature-specific tables.

**Changed before use:** Adopted. The database collector was additionally
changed to execute `schema.sql` and `seed.sql` in an in-memory SQLite
database, which proves the SQL runs and counts real rows for any student.

**Verification:** `REVIEW_TARGET=student-5 python agentic_loop.py` produced
evidence naming `transactions`, 14 seeded rows and 5 CHECK constraints. Log
saved to `docs/agentic-logs/`.

---

## 3. What was rejected or corrected

Recorded because §4.6 requires all AI output to be validated before use.

| Suggestion | Outcome |
|---|---|
| Separate `ai-service` container | Rejected — contradicts the specification's request workflow |
| Backend frontend proxy to avoid CORS | Rejected — the lab enables CORS instead; simpler and consistent with the team |
| Raw JSON passed to the LLM | Rejected — caused the model to describe data structures |
| POST probing in the agentic loop | Rejected — would create real transactions on every run |
| `host.docker.internal` as a local default | Rejected — only resolves inside a container |
| Letting the LLM total the transactions | Rejected — unacceptable hallucination risk for financial figures |

---

## 4. Summary

AI assistance was used for schema design, debugging, test design and review.
Every suggestion was checked against the specification, the registration form
or a running system before being accepted, and several were rejected on those
grounds. All submitted code was executed and verified locally before commit.
