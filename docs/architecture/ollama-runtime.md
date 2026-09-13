# Ollama Runtime — Architecture Decision Record

**Group 44 · Release 0 · ASD 2026**
Status: **Accepted** · Last updated: 5 September 2026

---

## 1. Decision

The team runs **Ollama on the host machine as an external runtime dependency**, not as a
container inside `docker-compose.yml`. Docker Compose builds and starts every application
microservice; the containerised backends reach the host Ollama runtime over the Docker
bridge network.

---

## 2. What Docker Compose builds and starts

One shared `docker-compose.yml` at the repository root builds and starts **13 containers**.
Every one is built from a Dockerfile in this repository — the file contains no `image:`
entries, so nothing is pulled from a registry.

| Service | Feature | Host port | Container port |
| `shared-index` | Shared HTMX entry point | 8080 | 8000 |
| `student-1-frontend` | Card Management | 8101 | 80 |
| `student-1-backend` | Card Management | 8201 | 5001 |
| `student-1-database` | Card Management | 8301 | 5002 |
| `student2-frontend` | Bank Account Management | 8102 | 80 |
| `student2-backend` | Bank Account Management | 8202 | 5001 |
| `student2-database` | Bank Account Management | 8302 | 5002 |
| `student4-frontend` | User Management | 8104 | 80 |
| `student4-backend` | User Management | 8204 | 5001 |
| `student4-database` | User Management | 8304 | 5002 |
| `student5-frontend` | Transaction Management | 8105 | 8000 |
| `student5-backend` | Transaction Management | 8205 | 8000 |
| `student5-db` | Transaction Management | 8305 | 8000 |

Host ports follow the team convention **frontend 810N, backend 820N, database 830N**,
where N is the student number.

Named volumes persist each SQLite database across restarts: `database_data`,
`student2_db_data`, `student4-database-data`, `student5-data`.

**Not started by Compose:**

- **Ollama** — runs on the host (see section 3).
- **The shared agentic loop** (`ai-services/agentic_loop/`) — a terminal program that is
  run on demand, not a long-running service. See section 7.
- **Student 3 (Notification Management)** — not yet contributed

## 3. Where Ollama runs, and why

Ollama runs **natively on each team member's machine**, listening on port `11434`. All four
containerised backends and the shared agentic loop use it as a shared AI runtime.

Four reasons for this arrangement:

**The specification already requires it locally.** Section 5.2 lists Ollama under Required
Software to be installed on every student's machine. Containerising it as well would mean
two Ollama installations and two copies of the same model weights on one machine, with no
functional gain.

**Hardware acceleration.** A containerised Ollama on the team's Apple Silicon machines falls
back to CPU inference and is measurably slower than the native install it would replace.

**Model storage.** A containerised Ollama stores model weights in a Docker volume, isolated
from the models each member already has under `~/.ollama`. Every member would re-download
the same weights they already hold on disk.

## 4. How containers resolve and connect to the host runtime

Containers address the host by the hostname **`host.docker.internal`**. Each backend that
uses AI-Mode declares:

```yaml
environment:
  OLLAMA_BASE_URL: http://host.docker.internal:11434/v1
extra_hosts:
  - "host.docker.internal:host-gateway"
```

```
Browser ──▶ Frontend container ──▶ Backend container ──▶ host.docker.internal:11434 ──▶ Ollama ──▶ Qwen 2.5
```

## 5. Configuration

Three environment variables control the connection. Compose supplies them to containers;
the values compiled into the code are development defaults used when a backend is run
directly on the host, outside Docker.

| Variable | Set in Compose to | Purpose |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434/v1` | Ollama's OpenAI-compatible endpoint |
| `OLLAMA_MODEL` | `qwen2.5:0.5b` | Model used for AI-Mode responses |
| `OLLAMA_REVIEW_MODEL` | `llama3.1:8b` | Second-pass review model, agentic loop and `student2-backend` only |

Every backend reads these with `os.getenv`. The shared agentic loop reads the same three variables in
`ai-services/agentic_loop/core/ai_runner.py`, but runs on the host, so it uses the
`localhost` default rather than the Compose value.

## 6. Evidence that AI-Mode works through this path

- **From the frontend.** Each feature's AI-Mode control returns a model-generated answer
  rendered in the browser. Screenshots are included in the technical report.
- **From the container.** `docker compose logs student5-backend` shows the outbound call to
  `host.docker.internal:11434` and a 200 response, proving the request originates inside a
  container rather than on the host.
- **From the runtime.** The Ollama server log records the matching inference request.
- **From the agentic loop.** Runs recorded under `docs/agentic-logs/` reach the same runtime
  from the host and complete all four phases, Plan → Act → Observe → Adapt.

## 7. Known limitations

- **Ollama is not started by `docker compose up`.** A machine without Ollama running will
  serve every feature correctly but return an error from AI-Mode controls. Section 6 lists
  it as a prerequisite.
- **Release 2 will require revisiting this decision**, since cloud deployment has no host
  runtime to connect to.
