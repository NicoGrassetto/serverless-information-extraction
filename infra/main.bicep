@description('Location for the Content Understanding service')
param location string = 'westus'

@description('Name for the Content Understanding service')
param serviceName string = 'content-understanding-${uniqueString(resourceGroup().id)}'

// Deploy Azure AI Content Understanding
resource contentUnderstanding 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: serviceName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: serviceName
    publicNetworkAccess: 'Enabled'
  }
}

// Outputs
output endpoint string = contentUnderstanding.properties.endpoint
output resourceId string = contentUnderstanding.id
output name string = contentUnderstanding.name
