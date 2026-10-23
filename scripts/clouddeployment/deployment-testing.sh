#!/bin/bash
set -e

# Validates the integrated cloud deployment for every student in STUDENTS and
# writes docs/cloud-deployment/deployment-results.md (evidence for the report).
# Run after scripts/clouddeployment/deploy-azure.sh.
#
# Per student it checks, through the PUBLIC frontend URL only:
#   1. the frontend page loads                          -> expect 200
#   2. one read endpoint, proxied by nginx to backend   -> expect 200 (frontend -> backend -> database)
#   3. the Multi-Agent route is not available in cloud  -> expect 403 (switched off), or 404/405 (no route)

RESOURCE_GROUP="${RESOURCE_GROUP:-clouddeployment-rg}"
STUDENTS="${STUDENTS:-student-1 student-2 student-4 student-5}"
REPORT_DIR="${REPORT_DIR:-docs/cloud-deployment}"
REPORT_FILE="$REPORT_DIR/deployment-results.md"

# One read-only API path per student, served by that student's backend.
api_path() {
    case "$1" in
        student-1) echo "/cards/by-id?card_id=1" ;;
        student-2) echo "/accounts" ;;
        student-4) echo "/users" ;;
        student-5) echo "/transactions?limit=5" ;;
        *)         echo "/" ;;
    esac
}

tag() { az group show --name "$RESOURCE_GROUP" --query "tags.\"$1\"" -o tsv 2>/dev/null || true; }

# curl with retries: a Container App may still be starting.
http_code() { # <method> <url>
    local code=""
    for _ in 1 2 3 4 5 6; do
        code=$(curl -s -o /dev/null -w "%{http_code}" -X "$1" --max-time 30 "$2" || true)
        if [[ "$code" != "000" && "$code" != "502" && "$code" != "503" && "$code" != "504" ]]; then
            break
        fi
        sleep 10
    done
    echo "${code:-000}"
}

echo "=== Cloud Deployment Testing ==="
mkdir -p "$REPORT_DIR"

ROWS=""
FAILED=0

for S in $STUDENTS; do
    APP_NAME=$(tag "$S-frontend")
    if [[ -z "$APP_NAME" ]]; then
        echo "No frontend tag for $S. Run env-setup.sh and deploy-azure.sh first." >&2
        exit 1
    fi
    FQDN=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" \
        --query properties.configuration.ingress.fqdn -o tsv)
    URL="https://$FQDN"
    API="$(api_path "$S")"

    PAGE=$(http_code GET "$URL/")
    READ=$(http_code GET "$URL$API")
    MA=$(http_code POST "$URL/multi-agent/workflow")

    RESULT="PASS"
    [[ "$PAGE" == "200" ]] || RESULT="FAIL"
    [[ "$READ" == "200" ]] || RESULT="FAIL"
    [[ "$MA" == "403" || "$MA" == "404" || "$MA" == "405" ]] || RESULT="FAIL"
    [[ "$RESULT" == "PASS" ]] || FAILED=1

    echo "$S  page=$PAGE  read($API)=$READ  multi-agent=$MA  -> $RESULT"
    ROWS+="| $S | $URL | $PAGE | \`$API\` $READ | $MA | $RESULT |"$'\n'
done

cat > "$REPORT_FILE" <<REPORT
# Cloud Deployment Report

Platform: Azure Container Apps
Resource group: $RESOURCE_GROUP
Commit: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)
Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)

| Student | Frontend URL | Page | Read endpoint (via frontend proxy) | Multi-Agent (expect 403/404/405) | Result |
|---|---|---|---|---|---|
$ROWS
Overall: $([[ $FAILED -eq 0 ]] && echo "Success" || echo "Failed")

AI-Mode, MCP, RAG and Multi-Agent are disabled in this deployment
(MCP_ENABLED, RAG_ENABLED, MULTI_AGENT_ENABLED = false on every backend).
REPORT

echo ""
cat "$REPORT_FILE"
echo "=== Deployment Testing Complete ==="
exit $FAILED