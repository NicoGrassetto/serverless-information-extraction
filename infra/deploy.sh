#!/bin/bash
# Enhanced Azure AI Content Understanding Deployment with cleanup

RESOURCE_GROUP="rg-document-intelligence"
LOCATION="westus"
DEPLOYMENT_NAME="main"

echo "🚀 Starting Azure AI Content Understanding deployment..."

# Check if resource group exists
echo "🔍 Checking if resource group exists..."
rg_exists=$(az group exists --name "$RESOURCE_GROUP" --output tsv)

if [ "$rg_exists" = "true" ]; then
    echo "📦 Resource group '$RESOURCE_GROUP' found."
    
    # Check for soft-deleted Cognitive Services accounts that might conflict
    echo "🔍 Checking for soft-deleted Cognitive Services accounts..."
    deleted_accounts=$(az cognitiveservices account list-deleted --query "[?location=='$LOCATION'].name" --output tsv 2>/dev/null)
    
    if [ ! -z "$deleted_accounts" ]; then
        echo "🗑️  Found soft-deleted Cognitive Services accounts. Purging them..."
        while IFS= read -r account_name; do
            if [ ! -z "$account_name" ]; then
                echo "   Purging: $account_name"
                az cognitiveservices account purge --name "$account_name" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" 2>/dev/null || echo "   ⚠️  Failed to purge $account_name"
            fi
        done <<< "$deleted_accounts"
        
        echo "⏳ Waiting for purge operations to complete..."
        sleep 20
    else
        echo "ℹ️  No soft-deleted accounts found in this location."
    fi
    
    # Check if previous deployment exists
    echo "🔍 Checking for previous deployments..."
    deployment_exists=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name "$DEPLOYMENT_NAME" --query "name" --output tsv 2>/dev/null)
    
    if [ ! -z "$deployment_exists" ]; then
        echo "🗑️  Previous deployment found. Cleaning up resources..."
        
        # Get list of resources to delete (excluding the resource group itself)
        resources=$(az resource list --resource-group "$RESOURCE_GROUP" --query "[].id" --output tsv 2>/dev/null)
        
        if [ ! -z "$resources" ]; then
            echo "🧹 Deleting existing resources..."
            while IFS= read -r resource_id; do
                echo "   Deleting: $resource_id"
                az resource delete --ids "$resource_id" --verbose 2>/dev/null || echo "   ⚠️  Failed to delete $resource_id (may not exist)"
            done <<< "$resources"
            
            # Wait a bit for deletions to complete
            echo "⏳ Waiting for resource cleanup to complete..."
            sleep 30
        else
            echo "ℹ️  No resources found in resource group."
        fi
    else
        echo "ℹ️  No previous deployment found."
    fi
else
    echo "📦 Creating resource group '$RESOURCE_GROUP'..."
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
fi

echo "🚀 Deploying new infrastructure..."

# Deploy the service
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "main.bicep" \
    --name "$DEPLOYMENT_NAME" \
    --mode "Incremental" \
    --verbose

if [ $? -eq 0 ]; then
    echo "✅ Deployment complete!"
    
    # Get the service details
    echo "📋 Service Details:"
    deployment_output=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name "$DEPLOYMENT_NAME" --query "properties.outputs" --output json)
    
    if command -v jq &> /dev/null; then
        echo "$deployment_output" | jq '.'
    else
        echo "$deployment_output"
    fi
else
    echo "❌ Deployment failed!"
    exit 1
fi
