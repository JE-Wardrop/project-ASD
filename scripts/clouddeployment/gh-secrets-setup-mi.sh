#!/bin/bash
set -e

# One-time, local-only alternative to gh-secrets-setup.sh.
# Use it when the Azure tenant blocks app registrations (UTS student accounts:
# "Insufficient privileges to complete the operation").
# Instead of an app registration it creates a user-assigned managed identity,
# trusts GitHub OIDC tokens from this repo + branch, grants it Contributor on the
# subscription, then pushes the IDs to GitHub Actions secrets (needs repo admin;
# without admin it prints the IDs so a repo admin can add them).

# Prevents Git Bash on Windows from rewriting "/subscriptions/..." into a local file path.
export MSYS_NO_PATHCONV=1

# Separate resource group so cleanup.sh (which deletes clouddeployment-rg) keeps the identity.
IDENTITY_RG="${IDENTITY_RG:-github-oidc-rg}"
IDENTITY_NAME="cloud-dev-github-oidc"
LOCATION="${LOCATION:-australiaeast}"
ISSUER="https://token.actions.githubusercontent.com"
AUDIENCE="api://AzureADTokenExchange"

echo "=== Cloud Development GitHub Secrets Setup (managed identity) ==="

if ! az account show >/dev/null 2>&1; then
    az login
fi
if ! gh auth status >/dev/null 2>&1; then
    gh auth login
fi

REPO_URL=$(git config --get remote.origin.url)
REPO_SLUG=$(echo "$REPO_URL" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')
BRANCH=$(git rev-parse --abbrev-ref HEAD)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "Repo: $REPO_SLUG   Branch: $BRANCH"
echo "Subscription: $(az account show --query name -o tsv)"

# Step 1: Resource group + managed identity (idempotent)
az group create --name "$IDENTITY_RG" --location "$LOCATION" --output none
az identity create --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RG" --location "$LOCATION" --output none
CLIENT_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RG" --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RG" --query principalId -o tsv)
echo "Managed identity ready: $IDENTITY_NAME"

# Step 2: Trust GitHub OIDC tokens from this repo + branch.
# Two subjects: the classic name-based format and GitHub's immutable ID-based format,
# so login works whichever one GitHub issues for this repo.
OWNER_NAME=$(echo "$REPO_SLUG" | cut -d/ -f1)
REPO_NAME=$(echo "$REPO_SLUG" | cut -d/ -f2)
OWNER_ID=$(gh api "repos/${REPO_SLUG}" --jq '.owner.id')
REPO_ID=$(gh api "repos/${REPO_SLUG}" --jq '.id')
SUBJECT_CLASSIC="repo:${REPO_SLUG}:ref:refs/heads/${BRANCH}"
SUBJECT_IMMUTABLE="repo:${OWNER_NAME}@${OWNER_ID}/${REPO_NAME}@${REPO_ID}:ref:refs/heads/${BRANCH}"

set_federated_credential() {
    local name="$1" subject="$2"
    if az identity federated-credential show --name "$name" \
         --identity-name "$IDENTITY_NAME" --resource-group "$IDENTITY_RG" >/dev/null 2>&1; then
        az identity federated-credential update --name "$name" \
          --identity-name "$IDENTITY_NAME" --resource-group "$IDENTITY_RG" \
          --issuer "$ISSUER" --subject "$subject" --audiences "$AUDIENCE" --output none
    else
        az identity federated-credential create --name "$name" \
          --identity-name "$IDENTITY_NAME" --resource-group "$IDENTITY_RG" \
          --issuer "$ISSUER" --subject "$subject" --audiences "$AUDIENCE" --output none
    fi
    echo "Federated credential '$name' -> $subject"
}
set_federated_credential "github-classic" "$SUBJECT_CLASSIC"
set_federated_credential "github-immutable" "$SUBJECT_IMMUTABLE"

# Step 3: Contributor on the subscription (enough for env-setup, ACR admin creds, Container Apps).
# User Access Administrator is not needed: deploy-azure.sh uses ACR admin credentials,
# not --registry-identity system.
# --assignee-object-id avoids a directory lookup that student accounts may not be allowed to do.
if az role assignment create \
     --assignee-object-id "$PRINCIPAL_ID" \
     --assignee-principal-type ServicePrincipal \
     --role Contributor \
     --scope "/subscriptions/$SUBSCRIPTION_ID" --output none; then
    echo "Granted Contributor role."
else
    echo "Role assignment failed. If the error above says it already exists, this is fine."
fi

# Step 4: Push the IDs to GitHub Actions secrets (needs repo admin)
if gh secret set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID" \
   && gh secret set AZURE_TENANT_ID --body "$TENANT_ID" \
   && gh secret set AZURE_CLIENT_ID --body "$CLIENT_ID"; then
    echo "Pushed AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, and AZURE_CLIENT_ID to GitHub Actions secrets."
else
    echo ""
    echo "Could not set GitHub secrets (repo admin needed). Ask a repo admin to add these"
    echo "under Settings -> Secrets and variables -> Actions -> New repository secret:"
    echo "  AZURE_SUBSCRIPTION_ID = $SUBSCRIPTION_ID"
    echo "  AZURE_TENANT_ID       = $TENANT_ID"
    echo "  AZURE_CLIENT_ID       = $CLIENT_ID"
fi

echo "=== GitHub Secrets Setup Complete ==="
echo "Only workflow runs on branch '$BRANCH' can log in. Re-run this script on another branch to switch."