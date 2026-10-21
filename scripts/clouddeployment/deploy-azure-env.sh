#!/bin/bash
set -e

# Creates the Container Apps environment
# (run env-setup.sh and build-images.sh first, scripts/clouddeployment/deploy-azure.sh after).
# Kept separate from deploy-azure.sh for OIDC token timing — see Section 6 "Why two refreshes".

echo "=== Cloud Container Apps Environment ==="

# Make sure the RESOURCE_GROUP is consistent with all the files.
RESOURCE_GROUP="${RESOURCE_GROUP:-clouddeployment-rg}"

# Step 1: Read deployment names from resource group tags
ENV_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.envName" -o tsv)
LOCATION=$(az group show --name "$RESOURCE_GROUP" --query "tags.location" -o tsv)

if [[ -z "$ENV_NAME" || -z "$LOCATION" ]]; then
    echo "Resource group $RESOURCE_GROUP is missing deployment tags. Run scripts/clouddeployment/env-setup.sh first." >&2
    exit 1
fi

# Step 2: Create Container Apps environment
if az containerapp env show --name "$ENV_NAME" --resource-group "$RESOURCE_GROUP" -o none 2>/dev/null; then
    echo "Container Apps environment $ENV_NAME already exists."
else
    echo "Creating Container Apps environment..."
    az containerapp env create \
        --name "$ENV_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION"
fi

echo "=== Container Apps Environment Ready ==="