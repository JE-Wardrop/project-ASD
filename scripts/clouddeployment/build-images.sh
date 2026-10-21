#!/bin/bash
set -e

# Creates the container registry and builds/pushes the frontend, backend and
# database images of every student in STUDENTS
# (run scripts/clouddeployment/env-setup.sh first, deploy-azure-env.sh after).
#
# Kept as its own step (like Lab 11) so CI can refresh the Azure login before
# the slow environment and deployment steps.

echo "=== Cloud Image Build ==="

RESOURCE_GROUP="${RESOURCE_GROUP:-clouddeployment-rg}"
STUDENTS="${STUDENTS:-student-1 student-2 student-4 student-5}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo latest)}"

# Step 1: Read the registry name from resource group tags
REGISTRY_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.registryName" -o tsv)
LOCATION=$(az group show --name "$RESOURCE_GROUP" --query "tags.location" -o tsv)

if [[ -z "$REGISTRY_NAME" || -z "$LOCATION" ]]; then
    echo "Resource group $RESOURCE_GROUP is missing deployment tags. Run scripts/clouddeployment/env-setup.sh first." >&2
    exit 1
fi

# Step 2: Create the container registry (images for every student go into this one registry)
if az acr show --name "$REGISTRY_NAME" --resource-group "$RESOURCE_GROUP" -o none 2>/dev/null; then
    echo "Registry $REGISTRY_NAME already exists."
else
    echo "Creating Azure Container Registry..."
    az acr create \
        --name "$REGISTRY_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Basic
fi

# Step 2b: Wait for the registry's DNS name to propagate before building.
# A fresh ACR can report "created" before *.azurecr.io resolves, causing
# the first `az acr build` push to fail with "no such host".
LOGIN_SERVER="${REGISTRY_NAME}.azurecr.io"
echo "Waiting for $LOGIN_SERVER to resolve..."
for i in $(seq 1 24); do
    # getent on Linux (CI), nslookup on Git Bash (Windows)
    if getent hosts "$LOGIN_SERVER" >/dev/null 2>&1 || nslookup "$LOGIN_SERVER" >/dev/null 2>&1; then
        echo "$LOGIN_SERVER is resolvable."
        break
    fi
    if [[ "$i" -eq 24 ]]; then
        echo "Timed out waiting for $LOGIN_SERVER to resolve." >&2
        exit 1
    fi
    sleep 5
done

# Accepts both "Dockerfile" and "dockerfile".
find_dockerfile() { # <student> <service>
    local dir="$REPO_ROOT/$1/$2" f
    for f in Dockerfile dockerfile; do
        if [[ -f "$dir/$f" ]]; then echo "$dir/$f"; return 0; fi
    done
    return 1
}

# Step 3: Validate every student before building anything (fail fast)
for S in $STUDENTS; do
    for SVC in database backend frontend; do
        find_dockerfile "$S" "$SVC" >/dev/null || { echo "Missing Dockerfile: $S/$SVC" >&2; exit 1; }
    done
done

# Step 4: Build and push every image in ACR (no local Docker needed).
# The build context is the service folder itself, e.g. student-2/backend.
for S in $STUDENTS; do
    for SVC in database backend frontend; do
        DF=$(find_dockerfile "$S" "$SVC")
        echo "Building and pushing $S/$SVC:$IMAGE_TAG..."
        az acr build \
            --registry "$REGISTRY_NAME" \
            --image "$S/$SVC:$IMAGE_TAG" \
            --file "$(basename "$DF")" \
            "$REPO_ROOT/$S/$SVC"
    done
done

echo "=== Image Build Complete ==="
