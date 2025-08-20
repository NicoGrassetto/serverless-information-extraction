# Simple Azure AI Content Understanding Deployment

$ResourceGroup = "rg-document-intelligence"
$Location = "westus"

Write-Host "🚀 Deploying Azure AI Content Understanding..." -ForegroundColor Green

# Deploy the service
az deployment group create `
    --resource-group $ResourceGroup `
    --template-file "main.bicep" `
    --location $Location

Write-Host "✅ Deployment complete!" -ForegroundColor Green

# Get the service details
Write-Host "📋 Service Details:" -ForegroundColor Cyan
$deploymentOutput = az deployment group show --resource-group $ResourceGroup --name "main" --query "properties.outputs" --output json | ConvertFrom-Json

$deploymentOutput | ConvertTo-Json -Depth 3
