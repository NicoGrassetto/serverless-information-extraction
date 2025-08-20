#!/bin/bash
# Simple Azure AI Content Understanding Deployment

RESOURCE_GROUP="rg-document-intelligence"
LOCATION="westus"

echo "🚀 Deploying Azure AI Content Understanding..."

# Deploy the service
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "main.bicep" \
    --location "$LOCATION"

echo "✅ Deployment complete!"

# Get the service details
echo "📋 Service Details:"
deployment_output=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name "main" --query "properties.outputs" --output json)
echo "$deployment_output" | jq '.'
