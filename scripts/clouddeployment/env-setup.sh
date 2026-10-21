#!/bin/bash
set -e

# Creates the resource group and tags it with generated deployment names:
# one registry, one Container Apps environment, and a frontend / backend / database
# app name for each student. Only the students listed in STUDENTS are included.
# MCP, RAG and multi-agent servers are intentionally NOT part of this deployment.

RESOURCE_GROUP="${RESOURCE_GROUP:-clouddeployment-rg}"
LOCATION="${LOCATION:-australiaeast}"
STUDENTS="${STUDENTS:-student-1 student-2 student-4 student-5}"
SERVICES="frontend backend database"

echo "=== Cloud Environment Setup ==="

echo "Registering required resource providers (skips if already registered)..."
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

EXISTING_REGISTRY=$(az group show --name "$RESOURCE_GROUP" --query "tags.registryName" -o tsv 2>/dev/null || true)

if [[ -n "$EXISTING_REGISTRY" ]]; then
    echo "Resource group $RESOURCE_GROUP is already configured — reusing existing names."
    az group show --name "$RESOURCE_GROUP" --query tags -o table
    exit 0
fi

REGISTRY_NAME="cloudregistry${RANDOM}"
ENV_NAME="cloud-env-${RANDOM}"

TAGS=("registryName=$REGISTRY_NAME" "envName=$ENV_NAME" "location=$LOCATION")

# Tag key = "<student>-<service>", value = generated Container App name,
# e.g. student-1-backend=student-1-backend-12345
for S in $STUDENTS; do
    for SVC in $SERVICES; do
        TAGS+=("${S}-${SVC}=${S}-${SVC}-${RANDOM}")
    done
done

echo "Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "Tagging resource group with deployment names..."
az group update --name "$RESOURCE_GROUP" --tags "${TAGS[@]}"

echo "=== Environment Setup Complete ==="
az group show --name "$RESOURCE_GROUP" --query tags -o table