#!/usr/bin/env bash
# Stop every container. Database volumes are preserved.
#
# This script deliberately does NOT pass -v. That flag deletes the named volumes,
# which wipes every feature's SQLite data. If you really want a clean database,
# run "docker compose down -v" by hand so the choice is explicit.

# exit immediately if a command exits with a non-zero status, 
# treat unset variables as an error, and prevent errors in a pipeline from being masked
set -euo pipefail

# cd root directory of the project
cd "$(dirname "$0")/.."

# $@ = option
docker compose down "$@"

echo
echo "All containers stopped. Database volumes kept."
