#!/usr/bin/env bash
# Start the integrated application, then print where each feature is served.
# Ollama runs on the host, not in Compose - see docs/architecture/ollama-runtime.md

# exit immediately if a command exits with a non-zero status, 
# treat unset variables as an error, and prevent errors in a pipeline from being masked
set -euo pipefail

# cd root directory of the project
cd "$(dirname "$0")/.."

# check the host Ollama runtime before starting anything
if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama runtime: reachable on port 11434"
else
    echo "WARNING: Ollama is not answering on http://localhost:11434"
    echo "         Every feature will still work, but AI-Mode will return an error."
    echo "         Start it with 'ollama serve' (Linux: OLLAMA_HOST=0.0.0.0 ollama serve)"
    echo
fi

echo "Starting all services..."
# $@ = option
docker compose up -d "$@"

echo
docker compose ps

cat <<'PORTS'

  Shared home page      http://localhost:8080

  Card Management       http://localhost:8101   (student-1, Juno)
  Account Management    http://localhost:8102   (student-2, Binh)
  Notification Mgmt     http://localhost:8103   (student-3, Ivan - not yet implemented)
  User Management       http://localhost:8104   (student-4, Sang)
  Transaction Mgmt      http://localhost:8105   (student-5, Gia)

  Backends 820N, databases 830N, where N is the student number.

PORTS
