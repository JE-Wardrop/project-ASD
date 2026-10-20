#!/bin/bash
set -e

# Builds and deploys the frontend, backend and database of every student in STUDENTS
# (default: student-1 student-2 student-4 student-5 = 12 apps) to an existing Container Apps
# environment. Run scripts/cloud/env-setup.sh and scripts/cloud/deploy-azure-env.sh first.
#
# Per student, from  <repo-root>/<student>/{frontend,backend,database}/Dockerfile :
#   database -> internal ingress only
#   backend  -> internal ingress only, given the database URL
#   frontend -> external ingress (the only public-facing app), given the backend URL
#
# MCP, RAG and multi-agent servers are NOT built or deployed. Re-running the script
# updates apps that already exist.

echo "=== Cloud Azure Deployment ==="

RESOURCE_GROUP="${RESOURCE_GROUP:-clouddeployment-rg}"
STUDENTS="${STUDENTS:-student-1 student-2 student-4 student-5}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo latest)}"

tag() { az group show --name "$RESOURCE_GROUP" --query "tags.\"$1\"" -o tsv 2>/dev/null || true; }

# Accepts both "Dockerfile" and "dockerfile".
find_dockerfile() { # <student> <service>
    local dir="$REPO_ROOT/$1/$2" f
    for f in Dockerfile dockerfile; do
        if [[ -f "$dir/$f" ]]; then echo "$dir/$f"; return 0; fi
    done
    return 1
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
    echo "Resource group $RESOURCE_GROUP is missing deployment tags. Run scripts/cloud/env-setup.sh first." >&2
    exit 1
fi

REGISTRY_SERVER=$(az acr show --name "$REGISTRY_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)

# Step 2: Validate every student before building anything (fail fast)
for S in $STUDENTS; do
    for SVC in frontend backend database; do
        DF=$(find_dockerfile "$S" "$SVC") || { echo "Missing Dockerfile: $S/$SVC" >&2; exit 1; }
        [[ -n "$(get_port "$S" "$SVC" "$DF")" ]] || { echo "No port for $S/$SVC: add an EXPOSE line to its Dockerfile or set $(echo "${S}_${SVC}_PORT" | tr 'a-z-' 'A-Z_')." >&2; exit 1; }
        [[ -n "$(tag "$S-$SVC")" ]] || { echo "No app name tag for $S-$SVC. Run scripts/cloud/env-setup.sh first." >&2; exit 1; }
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
            --registry-identity system \
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

    # Step 3: Build images in ACR (no local Docker needed)
    for SVC in database backend frontend; do
        DF=$(find_dockerfile "$S" "$SVC")
        echo "Building $S/$SVC:$IMAGE_TAG..."
        az acr build \
            --registry "$REGISTRY_NAME" \
            --image "$S/$SVC:$IMAGE_TAG" \
            --file "$(basename "$DF")" \
            "$REPO_ROOT/$S/$SVC"
    done

    # Step 4: Database (internal only, no public access)
    echo "Deploying $S database..."
    deploy_app "$DB_APP_NAME" "${REGISTRY_SERVER}/$S/database:${IMAGE_TAG}" \
        "$(get_port "$S" database "$(find_dockerfile "$S" database)")" internal 0.5 1.0Gi 1 1
    DB_FQDN=$(app_fqdn "$DB_APP_NAME")

    # Step 5: Backend (internal only, talks to this student's database)
    # The AI-feature flags are explicitly disabled: no MCP, RAG or multi-agent in the cloud deployment.
    echo "Deploying $S backend..."
    deploy_app "$BACKEND_APP_NAME" "${REGISTRY_SERVER}/$S/backend:${IMAGE_TAG}" \
        "$(get_port "$S" backend "$(find_dockerfile "$S" backend)")" internal 0.5 1.0Gi 1 3 \
        DATABASE_SERVICE_URL="https://$DB_FQDN" \
        AI_MODE_ENABLED=false MCP_ENABLED=false RAG_ENABLED=false MULTI_AGENT_ENABLED=false
    BACKEND_FQDN=$(app_fqdn "$BACKEND_APP_NAME")

    # Step 6: Frontend (the only public-facing app for this student)
    echo "Deploying $S frontend..."
    deploy_app "$FRONTEND_APP_NAME" "${REGISTRY_SERVER}/$S/frontend:${IMAGE_TAG}" \
        "$(get_port "$S" frontend "$(find_dockerfile "$S" frontend)")" external 0.25 0.5Gi 1 3 \
        BACKEND_SERVICE_URL="https://$BACKEND_FQDN"
    FRONTEND_FQDN=$(app_fqdn "$FRONTEND_APP_NAME")

    SUMMARY+="  $S frontend: https://$FRONTEND_FQDN"$'\n'
done

echo ""
echo "=== Deployment Complete ==="
printf '%s' "$SUMMARY"
echo ""
echo "Validate with: scripts/cloud/deployment-testing.sh"