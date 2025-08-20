# Enhanced Azure AI Content Understanding Deployment with cleanup

$ResourceGroup = "rg-document-intelligence"
$Location = "westus"
$DeploymentName = "main"

Write-Host "🚀 Starting Azure AI Content Understanding deployment..." -ForegroundColor Green

# Check if resource group exists
Write-Host "🔍 Checking if resource group exists..." -ForegroundColor Yellow
$rgExists = az group exists --name $ResourceGroup --output tsv

if ($rgExists -eq "true") {
    Write-Host "📦 Resource group '$ResourceGroup' found." -ForegroundColor Cyan
    
    # Check for soft-deleted Cognitive Services accounts that might conflict
    Write-Host "🔍 Checking for soft-deleted Cognitive Services accounts..." -ForegroundColor Yellow
    try {
        $deletedAccounts = az cognitiveservices account list-deleted --query "[?location=='$Location']" --output json | ConvertFrom-Json
        
        if ($deletedAccounts) {
            Write-Host "🗑️  Found soft-deleted Cognitive Services accounts. Purging them..." -ForegroundColor Yellow
            foreach ($account in $deletedAccounts) {
                Write-Host "   Purging: $($account.name)" -ForegroundColor Gray
                az cognitiveservices account purge --name $account.name --resource-group $ResourceGroup --location $Location 2>$null
            }
            Write-Host "⏳ Waiting for purge operations to complete..." -ForegroundColor Yellow
            Start-Sleep -Seconds 20
        }
    }
    catch {
        Write-Host "ℹ️  Could not check for soft-deleted accounts, continuing..." -ForegroundColor Blue
    }
    
    # Check if previous deployment exists
    Write-Host "🔍 Checking for previous deployments..." -ForegroundColor Yellow
    $deploymentExists = $null
    try {
        $deploymentExists = az deployment group show --resource-group $ResourceGroup --name $DeploymentName --query "name" --output tsv 2>$null
    }
    catch {
        # Deployment doesn't exist, which is fine
    }
    
    if ($deploymentExists) {
        Write-Host "🗑️  Previous deployment found. Cleaning up resources..." -ForegroundColor Yellow
        
        # Get list of resources to delete (excluding the resource group itself)
        try {
            $resources = az resource list --resource-group $ResourceGroup --query "[].id" --output tsv 2>$null
            
            if ($resources) {
                Write-Host "🧹 Deleting existing resources..." -ForegroundColor Yellow
                $resources | ForEach-Object {
                    $resourceId = $_.Trim()
                    if ($resourceId) {
                        Write-Host "   Deleting: $resourceId" -ForegroundColor Gray
                        try {
                            az resource delete --ids $resourceId --verbose 2>$null
                        }
                        catch {
                            Write-Host "   ⚠️  Failed to delete $resourceId (may not exist)" -ForegroundColor Yellow
                        }
                    }
                }
                
                # Wait a bit for deletions to complete
                Write-Host "⏳ Waiting for resource cleanup to complete..." -ForegroundColor Yellow
                Start-Sleep -Seconds 30
            }
            else {
                Write-Host "ℹ️  No resources found in resource group." -ForegroundColor Blue
            }
        }
        catch {
            Write-Host "ℹ️  Error checking resources, continuing with deployment..." -ForegroundColor Blue
        }
    }
    else {
        Write-Host "ℹ️  No previous deployment found." -ForegroundColor Blue
    }
}
else {
    Write-Host "📦 Creating resource group '$ResourceGroup'..." -ForegroundColor Cyan
    az group create --name $ResourceGroup --location $Location
}

Write-Host "🚀 Deploying new infrastructure..." -ForegroundColor Green

# Deploy the service
az deployment group create `
    --resource-group $ResourceGroup `
    --template-file "main.bicep" `
    --name $DeploymentName `
    --mode "Incremental" `
    --verbose

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment complete!" -ForegroundColor Green
    
    # Get the service details
    Write-Host "📋 Service Details:" -ForegroundColor Cyan
    try {
        $deploymentOutput = az deployment group show --resource-group $ResourceGroup --name $DeploymentName --query "properties.outputs" --output json | ConvertFrom-Json
        $deploymentOutput | ConvertTo-Json -Depth 3
    }
    catch {
        Write-Host "⚠️  Could not retrieve deployment outputs" -ForegroundColor Yellow
    }
}
else {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    exit 1
}
