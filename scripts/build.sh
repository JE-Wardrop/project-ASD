#!/usr/bin/env bash
# Build every container image defined in the shared Docker Compose configuration.

# exit immediately if a command exits with a non-zero status, 
# treat unset variables as an error, and prevent errors in a pipeline from being masked
set -euo pipefail

# cd root directory of the project
cd "$(dirname "$0")/.."

echo "Building all service images..."
# $@ = option 
docker compose build "$@"

echo
echo "Build complete. Start the application with: ./scripts/run.sh"
