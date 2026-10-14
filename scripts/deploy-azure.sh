#!/bin/bash
set -e

# Deploys all 3 services to an existing Container Apps environment (run scripts/lab11/deploy-azure-env.sh first).

echo "=== Lab 11 Azure Deployment ==="

RESOURCE_GROUP="${RESOURCE_GROUP:-lab11-rg}"
IMAGE_TAG="latest"

# Step 1: Read deployment names from resource group tags
REGISTRY_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.registryName" -o tsv)
ENV_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.envName" -o tsv)
FRONTEND_APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.frontendAppName" -o tsv)
ENROLMENT_APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.enrolmentAppName" -o tsv)
DB_APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.dbAppName" -o tsv)

if [[ -z "$REGISTRY_NAME" || -z "$ENV_NAME" || -z "$FRONTEND_APP_NAME" || -z "$ENROLMENT_APP_NAME" || -z "$DB_APP_NAME" ]]; then
  echo "Resource group $RESOURCE_GROUP is missing deployment tags. Run scripts/env-setup.sh first." >&2
  exit 1
fi

REGISTRY_SERVER=$(az acr show --name "$REGISTRY_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)


# Step 2: Deploy database services for each student (internal only, no public access)
echo "Deploying database services..."
az containerapp create \
  --name "$DB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --image "${REGISTRY_SERVER}/database-service:${IMAGE_TAG}" \
  --target-port 5002 \
  --ingress internal \
  --registry-server "$REGISTRY_SERVER" \
  --registry-identity system \
  --cpu 0.5 --memory 1.0Gi \
  --min-replicas 1 --max-replicas 1

DB_FQDN=$(az containerapp show \
  --name "$DB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

# Step 3: Deploy backend services for each student (internal only, talks to database-service)
echo "Deploying enrolment-service..."
az containerapp create \
  --name "$ENROLMENT_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --image "${REGISTRY_SERVER}/enrolment-service:${IMAGE_TAG}" \
  --target-port 5001 \
  --ingress internal \
  --registry-server "$REGISTRY_SERVER" \
  --registry-identity system \
  --cpu 0.5 --memory 1.0Gi \
  --min-replicas 1 --max-replicas 3 \
  --env-vars \
    DATABASE_SERVICE_URL="https://$DB_FQDN" \
    AI_MODE_ENABLED=false MCP_ENABLED=false RAG_ENABLED=false MULTI_AGENT_ENABLED=false

ENROLMENT_FQDN=$(az containerapp show \
  --name "$ENROLMENT_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

# Step 4: Deploy frontend services for each student(the only public-facing app)
echo "Deploying frontend-service..."
az containerapp create \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --image "${REGISTRY_SERVER}/frontend-service:${IMAGE_TAG}" \
  --target-port 80 \
  --ingress external \
  --registry-server "$REGISTRY_SERVER" \
  --registry-identity system \
  --cpu 0.25 --memory 0.5Gi \
  --min-replicas 1 --max-replicas 3 \
  --env-vars ENROLMENT_SERVICE_URL="https://$ENROLMENT_FQDN"

FRONTEND_FQDN=$(az containerapp show \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "=== Deployment Complete ==="
echo "Frontend URL: https://$FRONTEND_FQDN"
echo ""
echo "Validate with: curl -I https://$FRONTEND_FQDN"