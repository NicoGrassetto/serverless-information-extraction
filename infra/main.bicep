@description('Location for the Content Understanding service')
param location string = 'westus'

@description('Name for the Content Understanding service')
param serviceName string = 'content-understanding-${uniqueString(resourceGroup().id)}'

@description('Name for the storage account')
param storageAccountName string = 'storage${uniqueString(resourceGroup().id)}'

@description('Names of blob containers to create')
param blobContainerNames array = [
  'documents'
  'processed'
  'output'
  'temp'
]

// Deploy Blob Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    encryption: {
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// Deploy Blob Service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

// Deploy Blob Containers
resource blobContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for containerName in blobContainerNames: {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
    metadata: {
      purpose: 'Information extraction workflow'
      environment: 'production'
    }
  }
}]

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
output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output storageAccountPrimaryEndpoints object = storageAccount.properties.primaryEndpoints
output blobContainerNames array = [for i in range(0, length(blobContainerNames)): blobContainers[i].name]
output blobServiceEndpoint string = storageAccount.properties.primaryEndpoints.blob
