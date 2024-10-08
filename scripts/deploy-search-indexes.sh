# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

#!/bin/bash
set -e

figlet Search Index

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "${DIR}/load-env.sh"
source "${DIR}/environments/infrastructure.env"

if [ -n "${IN_AUTOMATION}" ]
then

    if [ -n "${AZURE_ENVIRONMENT}" ] && [[ $AZURE_ENVIRONMENT == "AzureUSGovernment" ]]; then
        az cloud set --name AzureUSGovernment 
    fi

    az login --service-principal -u "$ARM_CLIENT_ID" -p "$ARM_CLIENT_SECRET" --tenant "$ARM_TENANT_ID"
    az account set -s "$ARM_SUBSCRIPTION_ID"
fi

search_url="${AZURE_SEARCH_SERVICE_ENDPOINT}"

# Obtain an access token for Azure Search
access_token=$(az account get-access-token --resource $TF_VAR_azure_search_scope --query accessToken -o tsv)

# Fetch existing index definition if it exists
index_vector_json=$(cat ${DIR}/../azure_search/create_vector_index.json | envsubst | tr -d "\n" | tr -d "\r")
index_vector_name=$(echo $index_vector_json | jq -r .name )
existing_index=$(curl -s --header "Authorization: Bearer $access_token" $search_url/indexes/$index_vector_name?api-version=2024-05-01-preview)

if [[ "$existing_index" != *"No index with the name"* ]]; then
    existing_dimensions=$(echo "$existing_index" | jq -r '.fields | map(select(.name == "contentVector")) | .[0].dimensions')
    existing_index_name=$(echo "$existing_index" | jq -r '.name')
    # Compare existing dimensions with current $EMBEDDING_VECTOR_SIZE
    if [[ -n "$existing_dimensions" ]] && [[ "$existing_dimensions" != "$EMBEDDING_VECTOR_SIZE" ]]; then
        echo "Dimensions mismatch: Existing dimensions: $existing_dimensions, Current dimensions: $EMBEDDING_VECTOR_SIZE"
        read -p "Do you want to continue? This will delete the existing index and data! (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Operation aborted by the user."
            exit 0
        else
            echo "Deleting the existing index $existing_index_name..."
            curl -X DELETE --header "Authorization: Bearer $access_token" $search_url/indexes/$existing_index_name?api-version=2024-05-01-preview
            echo "Index $index_vector_name deleted."
        fi
    fi
fi    

# Create vector index
echo "Creating index $index_vector_name ..."
curl -s -X PUT --header "Content-Type: application/json" --header "Authorization: Bearer $access_token" --data "$index_vector_json" $search_url/indexes/$index_vector_name?api-version=2024-05-01-preview

echo -e "\n"
echo "Successfully deployed $index_vector_name."
