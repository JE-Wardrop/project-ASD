#!/bin/bash
set -e

# Validates every deployed student frontend and writes deployment-results.md
# (evidence for the agentic loop Deployment Review).
#
# For each student in STUDENTS:
#   GET https://<frontend>/        -> the public frontend is up
#   GET https://<frontend>/health  -> frontend -> backend -> database works
#                                     (only for students whose nginx proxies /health)

RESOURCE_GROUP="${RESOURCE_GROUP:-clouddeployment-rg}"
STUDENTS="${STUDENTS:-student-1 student-2 student-4 student-5}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# docs/report/ is where ai-services/agentic_loop/collectors/deployment_collector.py reads it
REPORT_DIR="${REPORT_DIR:-$REPO_ROOT/docs/report}"
REPORT_FILE="$REPORT_DIR/deployment-results.md"

tag() { az group show --name "$RESOURCE_GROUP" --query "tags.\"$1\"" -o tsv 2>/dev/null || true; }

http_code() { curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$1" || true; }

echo "=== Cloud Deployment Testing ==="

mkdir -p "$REPORT_DIR"
{
    echo "# Cloud Deployment Report"
    echo
    echo "## Azure Container Apps"
    echo
    echo "Resource Group: $RESOURCE_GROUP"
    echo
    echo "Commit: $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo
    echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "| Student | Frontend App | Frontend URL | Frontend | /health (via proxy) | Deployment Status |"
    echo "|---|---|---|---|---|---|"
} > "$REPORT_FILE"

FAILED=0

for S in $STUDENTS; do
    APP_NAME=$(tag "$S-frontend")

    if [[ -z "$APP_NAME" ]]; then
        echo "| $S | (no tag) | - | - | - | Failed |" >> "$REPORT_FILE"
        FAILED=1
        continue
    fi

    FQDN=$(az containerapp show \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || true)

    if [[ -z "$FQDN" ]]; then
        echo "| $S | $APP_NAME | - | not deployed | - | Failed |" >> "$REPORT_FILE"
        FAILED=1
        continue
    fi

    echo "Validating https://$FQDN ..."
    FRONT=$(http_code "https://$FQDN/")
    HEALTH=$(http_code "https://$FQDN/health")

    if [[ "$FRONT" == "200" ]]; then
        STATUS="Success"
    else
        STATUS="Failed"
        FAILED=1
    fi

    echo "| $S | $APP_NAME | https://$FQDN | HTTP $FRONT | HTTP $HEALTH | $STATUS |" >> "$REPORT_FILE"
done

{
    echo
    echo "Overall: $([[ $FAILED -eq 0 ]] && echo "All frontends returned HTTP 200" || echo "At least one deployment failed")"
    echo
    echo "Reviewer Notes: (pending agentic loop Deployment Review)"
} >> "$REPORT_FILE"

echo "=== Deployment Testing Complete ==="
cat "$REPORT_FILE"
