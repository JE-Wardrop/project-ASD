#!/bin/bash
set -e

# Creates the resource group and tags it with generated deployment names.

RESOURCE_GROUP="${RESOURCE_GROUP:-rg}"
LOCATION="${LOCATION:-australiaeast}"

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


STUDENT_1_FRONTEND="student-1-frontend-${RANDOM}"
STUDENT_1_BACKEND="student-1-backend-${RANDOM}"
STUDENT_1_DATABASE="student-1-database-${RANDOM}"

STUDENT_2_FRONTEND="student-2-frontend-${RANDOM}"
STUDENT_2_BACKEND="student-2-backend-${RANDOM}"
STUDENT_2_DATABASE="student-2-database-${RANDOM}"

STUDENT_4_FRONTEND="student-4-frontend-${RANDOM}"
STUDENT_4_BACKEND="student-4-backend-${RANDOM}"
STUDENT_4_DATABASE="student-4-database-${RANDOM}"

STUDENT_5_FRONTEND="student-5-frontend-${RANDOM}"
STUDENT_5_BACKEND="student-5-backend-${RANDOM}"
STUDENT_5_DATABASE="student-5-database-${RANDOM}"

echo "Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "Tagging resource group with deployment names..."
az group update \
  --name "$RESOURCE_GROUP" \
  --tags registryName="$REGISTRY_NAME" envName="$ENV_NAME" \
    frontendAppName="$STUDENT_1_FRONTEND" enrolmentAppName="$STUDENT_1_ENROLMENT" dbAppName="$STUDENT_1_DATABASE" \
    frontendAppName="$STUDENT_2_FRONTEND" enrolmentAppName="$STUDENT_2_ENROLMENT" dbAppName="$STUDENT_2_DATABASE" \
    frontendAppName="$STUDENT_4_FRONTEND" enrolmentAppName="$STUDENT_4_ENROLMENT" dbAppName="$STUDENT_4_DATABASE" \
    frontendAppName="$STUDENT_5_FRONTEND" enrolmentAppName="$STUDENT_5_ENROLMENT" dbAppName="$STUDENT_5_DATABASE" \
    location="$LOCATION"

echo "=== Environment Setup Complete ==="
az group show --name "$RESOURCE_GROUP" --query tags -o table