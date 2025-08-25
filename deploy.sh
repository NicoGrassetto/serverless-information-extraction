#!/bin/bash

# Serverless Information Extraction - Deployment Script
# This script deploys both the Azure infrastructure and the Azure Function

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="rg-info-extraction-dev"
BICEP_TEMPLATE="infra/main.bicep"
BICEP_PARAMETERS="infra/main.parameters.json"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if required tools are installed
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    # Check if Azure Functions Core Tools is installed
    if ! command -v func &> /dev/null; then
        print_error "Azure Functions Core Tools is not installed. Please install it from https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local"
        exit 1
    fi
    
    # Check if user is logged in to Azure
    if ! az account show &> /dev/null; then
        print_error "You are not logged in to Azure. Please run 'az login' first."
        exit 1
    fi
    
    print_success "All prerequisites are met!"
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_status "Starting infrastructure deployment..."
    
    # Check if resource group exists, create if it doesn't
    if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
        print_status "Creating resource group: $RESOURCE_GROUP"
        az group create --name "$RESOURCE_GROUP" --location "swedencentral"
        print_success "Resource group created successfully!"
    else
        print_status "Using existing resource group: $RESOURCE_GROUP"
    fi
    
    # Deploy Bicep template
    print_status "Deploying Bicep template..."
    DEPLOYMENT_OUTPUT=$(az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$BICEP_TEMPLATE" \
        --parameters "$BICEP_PARAMETERS" \
        --output json)
    
    if [ $? -eq 0 ]; then
        print_success "Infrastructure deployed successfully!"
        
        # Extract outputs for function deployment
        export FUNCTION_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.functionAppName.value')
        export STORAGE_ACCOUNT_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.storageAccountName.value')
        export COSMOS_DB_ACCOUNT_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.cosmosDbAccountName.value')
        
        print_status "Function App Name: $FUNCTION_APP_NAME"
        print_status "Storage Account Name: $STORAGE_ACCOUNT_NAME"
        print_status "Cosmos DB Account Name: $COSMOS_DB_ACCOUNT_NAME"
    else
        print_error "Infrastructure deployment failed!"
        exit 1
    fi
}

# Function to deploy Azure Function
deploy_function() {
    print_status "Starting function deployment..."
    
    if [ -z "$FUNCTION_APP_NAME" ]; then
        print_error "Function App name not found. Infrastructure deployment might have failed."
        exit 1
    fi
    
    # Check if function_app.py exists in the root directory
    if [ ! -f "function_app.py" ]; then
        print_error "function_app.py not found in the current directory. Please ensure you're running this script from the project root."
        exit 1
    fi
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found in the current directory."
        exit 1
    fi
    
    # Deploy the function
    print_status "Publishing function to Azure..."
    func azure functionapp publish "$FUNCTION_APP_NAME" --python
    
    if [ $? -eq 0 ]; then
        print_success "Function deployed successfully!"
        
        # Get the function URL
        FUNCTION_URL="https://${FUNCTION_APP_NAME}.azurewebsites.net"
        print_status "Function App URL: $FUNCTION_URL"
        print_status "Health Check URL: $FUNCTION_URL/api/health"
    else
        print_error "Function deployment failed!"
        exit 1
    fi
}

# Function to test deployment
test_deployment() {
    print_status "Testing deployment..."
    
    if [ -z "$FUNCTION_APP_NAME" ]; then
        print_warning "Cannot test deployment - Function App name not available"
        return
    fi
    
    HEALTH_URL="https://${FUNCTION_APP_NAME}.azurewebsites.net/api/health"
    
    print_status "Testing health endpoint: $HEALTH_URL"
    
    # Wait a moment for the function to be ready
    sleep 10
    
    # Test health endpoint
    if curl -f -s "$HEALTH_URL" > /dev/null; then
        print_success "Health check passed!"
    else
        print_warning "Health check failed. The function might still be starting up."
    fi
    
    # List deployed functions
    print_status "Listing deployed functions..."
    func azure functionapp list-functions "$FUNCTION_APP_NAME"
}

# Function to display post-deployment information
show_deployment_info() {
    print_success "Deployment completed successfully!"
    echo
    echo "=== Deployment Summary ==="
    echo "Resource Group: $RESOURCE_GROUP"
    echo "Function App: $FUNCTION_APP_NAME"
    echo "Storage Account: $STORAGE_ACCOUNT_NAME"
    echo "Cosmos DB Account: $COSMOS_DB_ACCOUNT_NAME"
    echo
    echo "=== Next Steps ==="
    echo "1. Visit the Azure Portal to verify resources are created"
    echo "2. Test the function by uploading files to the 'documents' container in the storage account"
    echo "3. Check Cosmos DB Data Explorer to see processed documents"
    echo "4. Monitor function execution in Azure Portal > Function App > Monitor"
    echo
    echo "=== Useful Commands ==="
    echo "Upload test file:"
    echo "  az storage blob upload --account-name $STORAGE_ACCOUNT_NAME --container-name documents --name test.txt --file sample-document.txt --auth-mode key"
    echo
    echo "Check function logs:"
    echo "  func azure functionapp logstream $FUNCTION_APP_NAME"
    echo
    echo "Health check:"
    echo "  curl https://${FUNCTION_APP_NAME}.azurewebsites.net/api/health"
}

# Main execution
main() {
    echo "=== Serverless Information Extraction Deployment ==="
    echo
    
    check_prerequisites
    deploy_infrastructure
    deploy_function
    test_deployment
    show_deployment_info
    
    print_success "All done! 🎉"
}

# Execute main function
main "$@"
