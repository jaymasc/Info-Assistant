#!/bin/bash

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
GENERATED_CONFIG_FILE="${DIR}/..//app/frontend/src/authConfig.generated.ts"
TERRAFORM_DIR="${DIR}/..//infra"

# Fetch Terraform outputs
APP_CLIENT_ID=$(terraform -chdir=$TERRAFORM_DIR output -raw AZURE_AD_APP_CLIENT_ID)
TENANT_ID=$(terraform -chdir=$TERRAFORM_DIR output -raw AZURE_TENANT_ID)
REDIRECT_URI=$(terraform -chdir=$TERRAFORM_DIR output -raw WEBAPP_REDIRECT_URI)

# Validate outputs
# if [[ -z "$APP_CLIENT_ID" || -z "$TENANT_ID" || -z "$REDIRECT_URI" ]]; then
if [[ -z "$APP_CLIENT_ID" || -z "$TENANT_ID" ]]; then
    echo "Error: One or more Terraform outputs are missing!"
    exit 1
fi

# Create the generated config file
cat <<EOL > "$GENERATED_CONFIG_FILE"
/**
 * Auto-generated authentication configuration values from deployed infrastructure
 */

export const config = {
    clientId: "${APP_CLIENT_ID}",
    tenantId: "${TENANT_ID}",
    redirectUri: "${REDIRECT_URI}"
};
EOL

echo "authConfig.generated.ts updated successfully!"
