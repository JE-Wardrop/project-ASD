#!/bin/bash
set -e

# Deletes the resource group and everything inside it.

RESOURCE_GROUP="${RESOURCE_GROUP:-clouddeployment-rg}"
STUDENTS="${STUDENTS:-student-1 student-2 student-4 student-5}"

echo "=== Cloud Cleanup ==="

tag() { az group show --name "$RESOURCE_GROUP" --query "tags.\"$1\"" -o tsv 2>/dev/null || true; }

REGISTRY_NAME=$(tag registryName)
ENV_NAME=$(tag envName)

if [[ -z "$REGISTRY_NAME" ]]; then
    echo "Resource group $RESOURCE_GROUP not found or has no deployment tags — nothing to clean up." >&2
    exit 0
fi

echo "This will permanently delete resource group: $RESOURCE_GROUP"
echo "  Registry: $REGISTRY_NAME"
echo "  Environment: $ENV_NAME"
for S in $STUDENTS; do
    echo "  $S"
    echo "    Frontend App: $(tag "$S-frontend")"
    echo "    Backend App: $(tag "$S-backend")"
    echo "    Database App: $(tag "$S-database")"
done

if [[ -z "${CI:-}" ]]; then
    read -p "Type the resource group name to confirm: " CONFIRM
    if [[ "$CONFIRM" != "$RESOURCE_GROUP" ]]; then
        echo "Confirmation did not match. Aborting." >&2
        exit 1
    fi
fi

az group delete --name "$RESOURCE_GROUP" --yes --no-wait

echo "=== Deletion started ==="
echo "Resource group $RESOURCE_GROUP is being deleted in the background."
echo "Check progress with: az group show --name $RESOURCE_GROUP"