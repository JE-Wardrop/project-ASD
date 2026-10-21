#!/bin/bash
set -e

# Builds and deploys the frontend, backend and database of every student in STUDENTS
# (default: student-1 student-2 student-4 student-5 = 12 apps) to an existing
# Container Apps environment.
# Run scripts/clouddeployment/env-setup.sh and deploy-azure-env.sh first.
#
# Per student, from <repo-root>/<student>/{frontend,backend,database}/Dockerfile:
#   database -> internal ingress only
#   backend  -> internal ingress only, given the database URL
#   frontend -> external ingress (the only public-facing app), given the backend URL
#
# MCP, RAG and multi-agent servers are NOT built or deployed. Re-running the script
# updates apps that already exist.
#
# Azure for Students constraints this script works around:
#   - ACR Tasks ('az acr build') is blocked (TasksOperationsNotAllowed), so images are
#     built with the local Docker and pushed to the registry.
#   - The Container Apps environment is an "express" environment, which does not support
#     a system-assigned identity, so apps pull images with the registry's admin login.

echo "=== Cloud Azure Deployment ==="

RESOURCE_GROUP="${RESOURCE_GROUP:-clouddeployment-rg}"
STUDENTS="${STUDENTS:-student-1 student-2 student-4 student-5}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# The image tag is the commit id, so every commit deploys a new revision. With
# uncommitted changes the tag also gets a timestamp; otherwise Azure would see the
# same image name and keep running the old container.
if [[ -z "${IMAGE_TAG:-}" ]]; then
    IMAGE_TAG="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo latest)"
    if [[ -n "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null)" ]]; then
        IMAGE_TAG="${IMAGE_TAG}-dirty-$(date +%Y%m%d%H%M%S)"
        echo "Uncommitted changes found: using image tag $IMAGE_TAG"
    fi
fi

tag() { az group show --name "$RESOURCE_GROUP" --query "tags.\"$1\"" -o tsv 2>/dev/null || true; }

# Accepts both "Dockerfile" and "dockerfile", and returns the file's REAL name.
# macOS is case-insensitive, so [[ -f Dockerfile ]] is also true for "dockerfile",
# but Linux (the containers, GitHub Actions) is case-sensitive.
find_dockerfile() { # <student> <service>
    local dir="$REPO_ROOT/$1/$2" f
    f=$(find "$dir" -maxdepth 1 -type f \( -name Dockerfile -o -name dockerfile \) 2>/dev/null | head -n1)
    if [[ -n "$f" ]]; then echo "$f"; return 0; fi
    return 1
}

# Build context for a service: its own folder, the same as docker-compose.yml.
# (student-2's backend keeps prompts/ inside student-2/backend/, so it no longer
# needs the parent folder as its context.)
build_context() { # <student> <service>
    echo "$REPO_ROOT/$1/$2"
}

# Port comes from <STUDENT>_<SERVICE>_PORT (e.g. STUDENT_1_BACKEND_PORT) if set,
# otherwise from the first EXPOSE line of that service's Dockerfile. Nothing is assumed.
get_port() { # <student> <service> <dockerfile>
    local var
    var="$(echo "${1}_${2}_PORT" | tr 'a-z-' 'A-Z_')"
    if [[ -n "${!var:-}" ]]; then echo "${!var}"; return 0; fi
    grep -iE '^[[:space:]]*EXPOSE[[:space:]]' "$3" | head -n1 | grep -oE '[0-9]+' | head -n1 || true
}

# Step 1: Read deployment names from resource group tags
REGISTRY_NAME=$(tag registryName)
ENV_NAME=$(tag envName)

if [[ -z "$REGISTRY_NAME" || -z "$ENV_NAME" ]]; then
    echo "Resource group $RESOURCE_GROUP is missing deployment tags. Run scripts/clouddeployment/env-setup.sh first." >&2
    exit 1
fi

REGISTRY_SERVER=$(az acr show --name "$REGISTRY_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)

# Step 2: Registry access
# Docker on this machine pushes the images; the Container Apps pull them with the
# registry's admin login (express environments cannot use a system-assigned identity).
az acr login --name "$REGISTRY_NAME"
az acr update --name "$REGISTRY_NAME" --admin-enabled true -o none
REGISTRY_USER=$(az acr credential show --name "$REGISTRY_NAME" --query username -o tsv)
REGISTRY_PASS=$(az acr credential show --name "$REGISTRY_NAME" --query "passwords[0].value" -o tsv)

# Step 3: Validate every student before building anything (fail fast)
for S in $STUDENTS; do
    for SVC in frontend backend database; do
        DF=$(find_dockerfile "$S" "$SVC") || { echo "Missing Dockerfile: $S/$SVC" >&2; exit 1; }
        [[ -n "$(get_port "$S" "$SVC" "$DF")" ]] || { echo "No port for $S/$SVC: add an EXPOSE line to its Dockerfile or set $(echo "${S}_${SVC}_PORT" | tr 'a-z-' 'A-Z_')." >&2; exit 1; }
        [[ -n "$(tag "$S-$SVC")" ]] || { echo "No app name tag for $S-$SVC. Run scripts/clouddeployment/env-setup.sh first." >&2; exit 1; }
    done
done

deploy_app() { # <app> <image> <port> <ingress> <cpu> <memory> <min> <max> [KEY=VALUE ...]
    local app=$1 image=$2 port=$3 ingress=$4 cpu=$5 mem=$6 min=$7 max=$8
    shift 8
    if az containerapp show --name "$app" --resource-group "$RESOURCE_GROUP" -o none 2>/dev/null; then
        echo "Updating $app..."
        local setargs=()
        if [[ $# -gt 0 ]]; then setargs=(--set-env-vars "$@"); fi
        az containerapp update \
            --name "$app" \
            --resource-group "$RESOURCE_GROUP" \
            --image "$image" \
            --cpu "$cpu" --memory "$mem" \
            --min-replicas "$min" --max-replicas "$max" \
            ${setargs[@]+"${setargs[@]}"}
    else
        echo "Creating $app..."
        local envargs=()
        if [[ $# -gt 0 ]]; then envargs=(--env-vars "$@"); fi
        az containerapp create \
            --name "$app" \
            --resource-group "$RESOURCE_GROUP" \
            --environment "$ENV_NAME" \
            --image "$image" \
            --target-port "$port" \
            --ingress "$ingress" \
            --registry-server "$REGISTRY_SERVER" \
            --registry-username "$REGISTRY_USER" \
            --registry-password "$REGISTRY_PASS" \
            --cpu "$cpu" --memory "$mem" \
            --min-replicas "$min" --max-replicas "$max" \
            ${envargs[@]+"${envargs[@]}"}
    fi
}

app_fqdn() {
    az containerapp show --name "$1" --resource-group "$RESOURCE_GROUP" \
        --query properties.configuration.ingress.fqdn -o tsv
}

SUMMARY=""

for S in $STUDENTS; do
    echo ""
    echo "##### $S #####"

    DB_APP_NAME=$(tag "$S-database")
    BACKEND_APP_NAME=$(tag "$S-backend")
    FRONTEND_APP_NAME=$(tag "$S-frontend")

    # Step 4: Build the 3 images with local Docker and push them to the registry.
    # --platform linux/amd64: Azure runs amd64; Apple Silicon Macs build arm64 by default.
    for SVC in database backend frontend; do
        DF=$(find_dockerfile "$S" "$SVC")
        echo "Building $S/$SVC:$IMAGE_TAG..."
        docker buildx build \
            --platform linux/amd64 \
            --file "$DF" \
            --tag "${REGISTRY_SERVER}/$S/$SVC:$IMAGE_TAG" \
            --push \
            "$(build_context "$S" "$SVC")"
    done

    # Step 5: Database (internal only, no public access)
    echo "Deploying $S database..."
    deploy_app "$DB_APP_NAME" "${REGISTRY_SERVER}/$S/database:${IMAGE_TAG}" \
        "$(get_port "$S" database "$(find_dockerfile "$S" database)")" internal 0.5 1.0Gi 1 1
    DB_FQDN=$(app_fqdn "$DB_APP_NAME")

    # Step 6: Backend (internal only, talks to this student's database)
    # The AI-feature flags are explicitly disabled: no AI-Mode, MCP, RAG or multi-agent in the cloud.
    echo "Deploying $S backend..."
    deploy_app "$BACKEND_APP_NAME" "${REGISTRY_SERVER}/$S/backend:${IMAGE_TAG}" \
        "$(get_port "$S" backend "$(find_dockerfile "$S" backend)")" internal 0.5 1.0Gi 1 3 \
        DATABASE_SERVICE_URL="https://$DB_FQDN" \
        AI_MODE_ENABLED=false MCP_ENABLED=false RAG_ENABLED=false MULTI_AGENT_ENABLED=false
    BACKEND_FQDN=$(app_fqdn "$BACKEND_APP_NAME")

    # Step 7: Frontend (the only public-facing app). Its nginx proxies API paths to BACKEND_URL.
    echo "Deploying $S frontend..."
    deploy_app "$FRONTEND_APP_NAME" "${REGISTRY_SERVER}/$S/frontend:${IMAGE_TAG}" \
        "$(get_port "$S" frontend "$(find_dockerfile "$S" frontend)")" external 0.25 0.5Gi 1 3 \
        BACKEND_URL="https://$BACKEND_FQDN"
    FRONTEND_FQDN=$(app_fqdn "$FRONTEND_APP_NAME")

    SUMMARY+="  $S frontend: https://$FRONTEND_FQDN"$'\n'
done

echo ""
echo "=== Deployment Complete ==="
printf '%s' "$SUMMARY"
echo ""
echo "Validate with: bash scripts/clouddeployment/deployment-testing.sh"