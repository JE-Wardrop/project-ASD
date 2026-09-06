# Agentic AI Banking Application

**Group 44 · ASD 2026 · Release 0**

An agentic AI banking application built as five integrated microservice feature sets.
Each student owns a frontend, a backend/API, and a SQLite database microservice. All of
them run together as one multi-container application under a single Docker Compose
configuration, with AI-Mode powered by a local Ollama runtime and approved open-source
LLMs.

---

## Team and features

| Student | Name | Feature | Frontend | Backend | Database |
|---|---|---|---|---|---|
| student-1 | Juno Wardrop | Card Management | 8101 | 8201 | 8301 |
| student-2 | Binh Nguyen | Bank Account Management | 8102 | 8202 | 8302 |
| student-3 | Ivan | Notification Management | 8103 | 8203 | 8303 |
| student-4 | Sang | User Management | 8104 | 8204 | 8304 |
| student-5 | Gia Tran | Transaction Management | 8105 | 8205 | 8305 |

The shared home page runs on **http://localhost:8080** and is the single entry point to
all five features.

Host ports follow the convention **frontend 810N, backend 820N, database 830N**, where N
is the student number. Inside the Docker network, containers address each other by
service name.

## Prerequisites

- **Docker Desktop** (macOS / Windows) or **Docker Engine with the Compose plugin** (Linux)
- **Ollama** — <https://ollama.com>
- **Python 3.11+** — only needed to run the tests or the agentic loop outside Docker
- **Git**

Ollama runs on the host rather than as a container. This is a deliberate architectural
decision; the reasoning, the cross-platform networking, and the alternative that was
tested and rejected are documented in
[`docs/architecture/ollama-runtime.md`].

## Setup

**1. Clone the repository**

```bash
git clone git@github.com:JE-Wardrop/project-ASD.git
cd project-ASD
```

**2. Pull the approved models**

```bash
ollama pull qwen2.5:0.5b
ollama pull llama3.1:8b      # only needed for the agentic loop's review pass
```

**3. Start the Ollama runtime**

On macOS and Windows the Ollama application starts it automatically. On Linux the runtime
must listen on all interfaces so containers can reach it:

```bash
OLLAMA_HOST=0.0.0.0 ollama serve
```

Confirm it answers:

```bash
curl http://localhost:11434/api/tags
```

**4. Build and start the application**

```bash
docker compose up -d --build
```

**5. Open the application**

<http://localhost:8080>

The first AI-Mode request after starting Ollama takes 20–30 seconds while the model loads
into memory. Later requests respond in a few seconds.

## Everyday commands

```bash
docker compose up -d          # start everything
docker compose ps             # check container status
docker compose logs -f <svc>  # follow one service's logs
docker compose down           # stop, keeping database volumes
docker compose down -v        # stop and DELETE all database data
```

> `down -v` removes the named volumes, which wipes every feature's SQLite data. Use plain
> `down` unless you intend to reset the databases.

## Helper scripts

`scripts/` wraps the commands above so nobody has to remember the flags.

| Script | What it does |
|---|---|
| `./scripts/build.sh` | Builds every image. Run it before recording a demo. |
| `./scripts/run.sh` | Checks the Ollama runtime, starts all services, prints every feature's URL. |
| `./scripts/test.sh` | Runs each student's pytest suite. Pass a name to run one: `./scripts/test.sh student-5` |
| `./scripts/stop.sh` | Stops all containers, keeping database volumes. |
| `./scripts/agentic-loop.sh student-5` | Runs the agentic loop against one student's services. |


A typical session:

```bash
chmod +x scripts/*.sh      # once, after cloning

./scripts/build.sh         # build the images
./scripts/run.sh           # start everything, print the URLs
./scripts/test.sh          # run the test suites
./scripts/stop.sh          # stop, keeping the databases
```

`test.sh` and `agentic-loop.sh` run Python on the host, so they choose an interpreter in
this order: a virtual environment you have already activated, then `.venv` at the
repository root, then `.venv` inside the student folder being tested, then `python3` from
`PATH`. Each run prints the interpreter it picked. If a dependency is missing the script
stops and tells you what to install rather than failing with a traceback.

`agentic-loop.sh` needs the containers running, so start with `run.sh` first.

> **On Windows**, run these from **Git Bash** (installed with Git for Windows) or WSL.
> They are bash scripts, so PowerShell and CMD cannot run them directly. The equivalent
> `docker compose` commands above work in any shell.


## Repository structure

```
.github/workflows/    per-student CI pipelines
ai-services/          shared agentic loop and its prompt assets
docs/                 architecture decisions, prompt engineering, agentic loop logs
shared/               shared home page, CSS theme, and assets
student-1/ … student-5/
                      each student's frontend, backend, database, tests, Dockerfiles
scripts/              build, test and deployment helper scripts
docker-compose.yml    one shared configuration for the whole application
agentic_loop.py       launcher for the shared agentic loop
```

Each `student-N/` directory holds that student's own `frontend/`, `backend/`,
`database/` and `tests/`, along with the Dockerfile for each tier.

## Architecture

Every database container owns its own SQLite schema and exposes CRUD through its database
API. **No backend reads another feature's database file** — cross-feature data is only ever
retrieved through the owning feature's API. For example, Transaction Management validates
accounts and balances by calling the Account service, never by opening its `.db` file.

AI-Mode follows the required request workflow:

```
Frontend → Backend/API → Ollama → LLM
```

There is no intermediate AI service between a backend and Ollama. Each backend holds its
own AI-Mode implementation and calls the shared Ollama runtime directly.

## Configuration

Compose supplies these to each backend that uses AI-Mode:

| Variable | Value | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434/v1` | Ollama's OpenAI-compatible endpoint |
| `OLLAMA_MODEL` | `qwen2.5:0.5b` | Model used for AI-Mode responses |
| `OLLAMA_REVIEW_MODEL` | `llama3.1:8b` | Second-pass review model for the agentic loop |
| `DATABASE_SERVICE_URL` | `http://<feature>-database:5002` | That feature's own database API |

Each service also declares `extra_hosts: - "host.docker.internal:host-gateway"`, which is
what makes the host runtime reachable on Linux as well as on Docker Desktop.

## Running the tests

```bash
cd student-N #N is the student number
pip install -r requirements.txt
pytest tests/ -v
```

Each student's tests live under their own `student-N/tests/` directory and run
automatically in that student's GitHub Actions workflow on every push.

## Agentic AI workflow

The shared agentic loop implements **Plan → Act → Observe → Adapt**. It collects real
evidence from a target student's services — executing the schema, counting seeded rows,
calling health endpoints — then asks the model what should change based only on that
evidence.

Start the containers first, since the loop makes live HTTP calls, then:

```bash
pip install -r ai-services/agentic_loop/requirements.txt
REVIEW_TARGET=student-N python agentic_loop.py
```

Choose a review type from the menu (1 Database, 2 Endpoints, 3 Architecture, 4 DevOps,
5 all four). **Press 0 to quit** — the transcript is only written to
`docs/agentic-logs/` when you exit with 0.

Any student folder can be reviewed by changing `REVIEW_TARGET`.

## Continuous integration

Each student maintains their own workflow file in `.github/workflows/`. A push that
touches `student-N/` runs that student's pipeline, so one feature failing to build does
not turn another student's workflow red.

## Documentation

| Document                                                                     | Contents                                                                      |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| [`docs/architecture/ollama-runtime.md`](docs/architecture/ollama-runtime.md) | Where Ollama runs and why, cross-platform networking, alternatives considered |
| [`docs/prompts/`](docs/prompts/)                                             | Prompt engineering and AI context management records                          |
| [`docs/agentic-logs/`](docs/agentic-logs/)                                   | Recorded Plan → Act → Observe → Adapt runs                                    |

---

## Known issues and limitations

- **Notification Management (student-3) is not yet implemented** and has no services in
  `docker-compose.yml`.
- **Ollama is not started by `docker compose up`.** A machine without the runtime running
  serves every feature correctly but returns an error from AI-Mode controls.
