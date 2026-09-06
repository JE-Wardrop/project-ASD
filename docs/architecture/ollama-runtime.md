# Ollama Runtime — Architecture Decision Record

**Group 44 · Release 0 · ASD 2026**
Status: **Accepted** · Last updated: 5 September 2026

---

## 1. Decision

The team runs **Ollama on the host machine as an external runtime dependency**, not as a
container inside `docker-compose.yml`. Docker Compose builds and starts every application
microservice; the containerised backends reach the host Ollama runtime over the Docker
bridge network.

This arrangement was raised with the tutor before submission and confirmed as acceptable
for Release 0, on the condition that the boundary is made explicit and the setup is
reproducible. This document is that record.

---

## 2. What Docker Compose builds and starts

One shared `docker-compose.yml` at the repository root builds and starts **13 containers**.
Every one is built from a Dockerfile in this repository — the file contains no `image:`
entries, so nothing is pulled from a registry.

| Service | Feature | Host port | Container port |
|---|---|---|---|
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
- **Student 3 (Notification Management)** — not yet contributed. Recorded in the technical
  report under Known Issues and Limitations.

---

## 3. Where Ollama runs, and why

Ollama runs **natively on each team member's machine**, listening on port `11434`. All four
containerised backends and the shared agentic loop use it as a shared AI runtime.

Four reasons for this arrangement:

**The specification already requires it locally.** Section 5.2 lists Ollama under Required
Software to be installed on every student's machine. Containerising it as well would mean
two Ollama installations and two copies of the same model weights on one machine, with no
functional gain.

**Hardware acceleration.** Docker Desktop on macOS does not expose the Apple Silicon GPU
(Metal) to containers. A containerised Ollama on the team's Apple Silicon machines falls
back to CPU inference and is measurably slower than the native install it would replace.

**Model storage.** A containerised Ollama stores model weights in a Docker volume, isolated
from the models each member already has under `~/.ollama`. Every member would re-download
the same weights they already hold on disk.

**Consistency with the taught pattern.** The Release 0 lab template demonstrates exactly
this arrangement — application containers reaching a host-installed Ollama via
`host.docker.internal`.

The trade-off is that Ollama is a documented prerequisite rather than something
`docker compose up` provides. Section 6 covers how a new machine satisfies it.

---

## 4. How containers resolve and connect to the host runtime

Containers address the host by the hostname **`host.docker.internal`**. Each backend that
uses AI-Mode declares:

```yaml
    environment:
      OLLAMA_BASE_URL: http://host.docker.internal:11434/v1
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

The `extra_hosts` entry is what makes this portable across the operating systems in use by
the team:

| OS | Resolution | Extra step needed |
|---|---|---|
| **macOS** (Docker Desktop) | `host.docker.internal` resolves natively; the `extra_hosts` line is harmless | None |
| **Windows** (Docker Desktop) | Resolves natively, same as macOS | None |
| **Linux** (Docker Engine) | Does **not** resolve by default — the `host-gateway` mapping supplies it | Ollama must listen on all interfaces (below) |

**Linux note.** Ollama binds to `127.0.0.1` by default, which a container cannot reach even
once the hostname resolves. On Linux the runtime must be started as:

```bash
OLLAMA_HOST=0.0.0.0 ollama serve
```

On macOS and Windows, Docker Desktop's networking makes this unnecessary.

The full request path is therefore:

```
Browser ──▶ Frontend container ──▶ Backend container ──▶ host.docker.internal:11434 ──▶ Ollama ──▶ Qwen 2.5
```

This satisfies the specification's required AI request workflow,
**Frontend → Backend/API → Ollama → LLM**. No intermediate AI service sits between the
backend and Ollama.

---

## 5. Configuration

Three environment variables control the connection. Compose supplies them to containers;
the values compiled into the code are development defaults used when a backend is run
directly on the host, outside Docker.

| Variable | Set in Compose to | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434/v1` | Ollama's OpenAI-compatible endpoint |
| `OLLAMA_MODEL` | `qwen2.5:0.5b` | Model used for AI-Mode responses |
| `OLLAMA_REVIEW_MODEL` | `llama3.1:8b` | Second-pass review model, agentic loop and `student2-backend` only |

Every backend reads these with `os.getenv`, so Compose always wins over the compiled
default. The shared agentic loop reads the same three variables in
`ai-services/agentic_loop/core/ai_runner.py`, but runs on the host, so it uses the
`localhost` default rather than the Compose value.

`docker-compose.yml` also retains the containerised alternative as a commented line beside
the active one, so the decision is visible at the point of configuration:

```yaml
      OLLAMA_BASE_URL: http://host.docker.internal:11434/v1
      # OLLAMA_BASE_URL: http://ollama:11434/v1
```

---

## 6. Reproducing the setup on a new machine

1. Install Docker Desktop (macOS/Windows) or Docker Engine with the Compose plugin (Linux).
2. Install Ollama from <https://ollama.com>.
3. Pull the approved models:
   ```bash
   ollama pull qwen2.5:0.5b
   ollama pull llama3.1:8b     # only needed for the agentic loop's review pass
   ```
4. Start the runtime. On macOS and Windows the Ollama application starts it automatically.
   On Linux:
   ```bash
   OLLAMA_HOST=0.0.0.0 ollama serve
   ```
5. Confirm it answers:
   ```bash
   curl http://localhost:11434/api/tags
   ```
6. Start the application:
   ```bash
   git clone https://github.com/JE-Wardrop/project-ASD.git
   cd project-ASD
   docker compose up -d --build
   ```
7. Open <http://localhost:8080> and use AI-Mode in any feature.

The first AI-Mode call after starting Ollama takes 20–30 seconds while the model is loaded
into memory. Subsequent calls respond in a few seconds.

---

## 7. Evidence that AI-Mode works through this path

- **From the frontend.** Each feature's AI-Mode control returns a model-generated answer
  rendered in the browser. Screenshots are included in the technical report.
- **From the container.** `docker compose logs student5-backend` shows the outbound call to
  `host.docker.internal:11434` and a 200 response, proving the request originates inside a
  container rather than on the host.
- **From the runtime.** The Ollama server log records the matching inference request.
- **From the agentic loop.** Runs recorded under `docs/agentic-logs/` reach the same runtime
  from the host and complete all four phases, Plan → Act → Observe → Adapt.

---

## 8. Alternative considered: Ollama as a Compose service

The team implemented and tested a containerised Ollama service before choosing the host
arrangement. It was rejected on measured grounds, not assumption.

| Factor | Host runtime (chosen) | Containerised service |
|---|---|---|
| **Image size** | None — already installed per §5.2 | `ollama/ollama` ≈ 1.7 GB per machine, before models |
| **Model storage** | Shared `~/.ollama`, one copy | Separate Docker volume; every member re-downloads weights they already hold |
| **Hardware access** | Native Metal / CUDA | No GPU passthrough on macOS; CPU-only inference on the team's Apple Silicon machines |
| **Startup time** | Runtime already running; `up` is seconds | First `up` must pull the image and the models. In our test this stalled for 45 minutes on the image pull and had to be abandoned |
| **Portability** | Ollama is a documented prerequisite | Self-contained — the strongest argument for this option |
| **Reproducibility** | Six documented steps (§6) | `docker compose up` alone, once the pull succeeds |

Portability is the genuine advantage of the containerised option, and it is the arrangement
the team expects to revisit for Release 2's cloud deployment, where no host runtime exists
and a container is the only option. For Release 0 — local deployment only, on five
developer machines that are already required to have Ollama installed — the host runtime
delivers the same functional outcome at materially lower cost.

---

## 9. Known limitations

- **Ollama is not started by `docker compose up`.** A machine without Ollama running will
  serve every feature correctly but return an error from AI-Mode controls. Section 6 lists
  it as a prerequisite.
- **The compiled defaults are not uniform.** `student-1` and `student-2` default
  `OLLAMA_BASE_URL` to `host.docker.internal`, while `student-4`, `student-5` and the
  agentic loop default to `localhost`. Compose overrides all of them, so containers behave
  identically; the difference is visible only when a backend is run directly on the host.
  Standardising on `localhost` is planned for Release 1.
- **Release 2 will require revisiting this decision**, since cloud deployment has no host
  runtime to connect to.
