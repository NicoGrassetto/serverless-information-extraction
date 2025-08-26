# Serverless Information Extraction - Deployment Script (PowerShell)
# This script deploys both the Azure infrastructure and the Azure Function

param(
    [string]$ResourceGroup = "rg-info-extraction-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    [string]$BicepTemplate = "infra/main.bicep",
    [string]$BicepParameters = "infra/main.parameters.json"
)

# Enable strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to check if required tools are installed
function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check if Azure CLI is installed
    try {
        $null = Get-Command az -ErrorAction Stop
    }
    catch {
        Write-Error "Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    }
    
    # Check if Azure Functions Core Tools is installed
    try {
        $null = Get-Command func -ErrorAction Stop
    }
    catch {
        Write-Error "Azure Functions Core Tools is not installed. Please install it from https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local"
        exit 1
    }
    
    # Check if user is logged in to Azure
    try {
        $null = az account show 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Not logged in"
        }
    }
    catch {
        Write-Error "You are not logged in to Azure. Please run 'az login' first."
        exit 1
    }
    
    Write-Success "All prerequisites are met!"
}

# Function to deploy infrastructure
function Deploy-Infrastructure {
    Write-Status "Starting infrastructure deployment..."
    
    # Check if resource group exists, create if it doesn't
    $resourceGroupExists = az group show --name $ResourceGroup 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Status "Creating resource group: $ResourceGroup"
        az group create --name $ResourceGroup --location "swedencentral"
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Resource group created successfully!"
        } else {
            Write-Error "Failed to create resource group"
            exit 1
        }
    } else {
        Write-Status "Using existing resource group: $ResourceGroup"
    }
    
    # Deploy Bicep template
    Write-Status "Deploying Bicep template..."
    $deploymentOutput = az deployment group create `
        --resource-group $ResourceGroup `
        --template-file $BicepTemplate `
        --parameters $BicepParameters `
        --output json | ConvertFrom-Json
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Infrastructure deployed successfully!"
        
        # Extract outputs for function deployment
        $script:FunctionAppName = $deploymentOutput.properties.outputs.functionAppName.value
        $script:StorageAccountName = $deploymentOutput.properties.outputs.storageAccountName.value
        $script:CosmosDbAccountName = $deploymentOutput.properties.outputs.cosmosDbAccountName.value
        
        Write-Status "Function App Name: $script:FunctionAppName"
        Write-Status "Storage Account Name: $script:StorageAccountName"
        Write-Status "Cosmos DB Account Name: $script:CosmosDbAccountName"
    } else {
        Write-Error "Infrastructure deployment failed!"
        exit 1
    }
}

# Function to deploy Azure Function
function Deploy-Function {
    Write-Status "Starting function deployment..."
    
    if (-not $script:FunctionAppName) {
        Write-Error "Function App name not found. Infrastructure deployment might have failed."
        exit 1
    }
    
    # Check if function_app.py exists in the root directory
    if (-not (Test-Path "function_app.py")) {
        Write-Error "function_app.py not found in the current directory. Please ensure you're running this script from the project root."
        exit 1
    }
    
    # Check if requirements.txt exists
    if (-not (Test-Path "requirements.txt")) {
        Write-Error "requirements.txt not found in the current directory."
        exit 1
    }
    
    # Deploy the function
    Write-Status "Publishing function to Azure..."
    func azure functionapp publish $script:FunctionAppName --python
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Function deployed successfully!"
        
        # Get the function URL
        $script:FunctionUrl = "https://$($script:FunctionAppName).azurewebsites.net"
        Write-Status "Function App URL: $script:FunctionUrl"
        Write-Status "Health Check URL: $script:FunctionUrl/api/health"
    } else {
        Write-Error "Function deployment failed!"
        exit 1
    }
}

# Function to test deployment
function Test-Deployment {
    Write-Status "Testing deployment..."
    
    if (-not $script:FunctionAppName) {
        Write-Warning "Cannot test deployment - Function App name not available"
        return
    }
    
    $healthUrl = "https://$($script:FunctionAppName).azurewebsites.net/api/health"
    
    Write-Status "Testing health endpoint: $healthUrl"
    
    # Wait a moment for the function to be ready
    Start-Sleep -Seconds 10
    
    # Test health endpoint
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Success "Health check passed!"
        } else {
            Write-Warning "Health check returned status code: $($response.StatusCode)"
        }
    }
    catch {
        Write-Warning "Health check failed. The function might still be starting up."
    }
    
    # List deployed functions
    Write-Status "Listing deployed functions..."
    func azure functionapp list-functions $script:FunctionAppName
}

# Function to display post-deployment information
function Show-DeploymentInfo {
    Write-Success "Deployment completed successfully!"
    Write-Host ""
    Write-Host "=== Deployment Summary ===" -ForegroundColor Cyan
    Write-Host "Resource Group: $ResourceGroup"
    Write-Host "Function App: $script:FunctionAppName"
    Write-Host "Storage Account: $script:StorageAccountName"
    Write-Host "Cosmos DB Account: $script:CosmosDbAccountName"
    Write-Host ""
    Write-Host "=== Next Steps ===" -ForegroundColor Cyan
    Write-Host "1. Visit the Azure Portal to verify resources are created"
    Write-Host "2. Test the function by uploading files to the 'documents' container in the storage account"
    Write-Host "3. Check Cosmos DB Data Explorer to see processed documents"
    Write-Host "4. Monitor function execution in Azure Portal > Function App > Monitor"
    Write-Host ""
    Write-Host "=== Useful Commands ===" -ForegroundColor Cyan
    Write-Host "Upload test file:"
    Write-Host "  az storage blob upload --account-name $script:StorageAccountName --container-name documents --name test.txt --file sample-document.txt --auth-mode key"
    Write-Host ""
    Write-Host "Check function logs:"
    Write-Host "  func azure functionapp logstream $script:FunctionAppName"
    Write-Host ""
    Write-Host "Health check:"
    Write-Host "  curl https://$($script:FunctionAppName).azurewebsites.net/api/health"
}

# Main execution
function Main {
    Write-Host "=== Serverless Information Extraction Deployment ===" -ForegroundColor Magenta
    Write-Host ""
    
    try {
        Test-Prerequisites
        Deploy-Infrastructure
        Deploy-Function
        Test-Deployment
        Show-DeploymentInfo
        
        Write-Success "All done! 🎉"
    }
    catch {
        Write-Error "Deployment failed: $($_.Exception.Message)"
        exit 1
    }
}

# Execute main function
Main
