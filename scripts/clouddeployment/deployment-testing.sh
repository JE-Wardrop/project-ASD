#!/bin/bash
set -e

# Validates the deployed frontend's health endpoint and writes deployment-results.md.

RESOURCE_GROUP="${RESOURCE_GROUP:-lab11-rg}"
REPORT_FILE="reports/lab11/deployment-results.md"

echo "=== Lab 11 Deployment Testing ==="

# Step 1: Read the deployed frontend Container App name from resource group tags
APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.frontendAppName" -o tsv)

if [[ -z "$APP_NAME" ]]; then
  echo "Resource group $RESOURCE_GROUP is missing the frontendAppName tag. Run scripts/lab11/env-setup.sh and scripts/lab11/deploy-azure.sh first." >&2
  exit 1
fi

# Step 2: Get the Container App FQDN
APP_URL=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

# Step 3: Validate the health endpoint
echo "Validating https://$APP_URL ..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$APP_URL")

if [[ "$HTTP_STATUS" == "200" ]]; then
  STATUS="Success"
  VALIDATION="HTTP $HTTP_STATUS OK"
else
  STATUS="Failed"
  VALIDATION="HTTP $HTTP_STATUS"
fi

# Step 4: Write deployment-results.md
mkdir -p reports/lab11
cat > "$REPORT_FILE" <<EOF
# Lab 11 Deployment Report

## Azure Container Apps

Deployment Status: $STATUS

Frontend App Name: $APP_NAME

Frontend URL: https://$APP_URL

Validation Result: $VALIDATION

Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)

Reviewer Notes: (pending Section 7 AI review)
EOF

echo "=== Deployment Testing Complete ==="
cat "$REPORT_FILE"