# Serverless Information Extraction

A serverless solution built on Azure that automatically processes documents uploaded to blob storage and extracts information using Azure Functions, with results stored in Cosmos DB.

## Architecture

This solution includes:

- **Azure Function App**: Python-based serverless compute triggered by blob uploads
- **Azure Blob Storage**: Document storage with `documents` and `processed` containers
- **Azure Cosmos DB**: NoSQL database for storing extracted information
- **Infrastructure as Code**: Bicep templates for consistent deployments

## Infrastructure

The infrastructure is defined in Bicep templates located in the `infra/` directory:

- `main.bicep`: Main infrastructure template
- `main.parameters.json`: Parameters file with configuration values

### Resources Created

1. **App Service Plan**: Consumption plan for serverless execution
2. **Storage Account**: 
   - `documents` container: For uploading files to be processed
   - `processed` container: For storing processed files (optional)
3. **Cosmos DB Account**: With SQL API
   - Database: `InformationExtractionDB`
   - Container: `ProcessedDocuments` (partitioned by `/id`)
4. **Function App**: Python 3.11 runtime with system-assigned managed identity
5. **Role Assignments**: Grants Function App access to Storage and Cosmos DB

## Function App

The Python Azure Function (`src/function_app.py`) includes:

### Main Function: `BlobTrigger`
- **Trigger**: Blob uploads to the `documents` container
- **Processing**: Extracts text and metadata from uploaded documents
- **Output**: Stores results in Cosmos DB with structured data

### Features
- Handles various file types (text, binary)
- Extracts basic metadata (file size, word count, etc.)
- Error handling with error document creation
- Health check endpoint at `/api/health`

## Deployment

### Prerequisites
- Azure CLI installed and authenticated
- Azure subscription with sufficient permissions

### Deploy Infrastructure

1. Clone this repository
2. Navigate to the project directory
3. Deploy using Azure CLI:

```bash
# Create resource group
az group create --name rg-info-extraction-dev --location swedencentral

# Deploy infrastructure
az deployment group create \
  --resource-group rg-info-extraction-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

### Deploy Function App

1. Install Azure Functions Core Tools
2. Deploy the function:

```bash
# Navigate to the project root
cd serverless-information-extraction

# Deploy function app (replace with your function app name)
func azure functionapp publish <your-function-app-name>
```

## Usage

### Upload Documents

Upload documents to the `documents` container in your storage account:

```bash
# Using Azure CLI
az storage blob upload \
  --account-name <storage-account-name> \
  --container-name documents \
  --name sample.txt \
  --file ./sample.txt
```

### View Results

Check the processed results in Cosmos DB:

1. Open Azure Portal
2. Navigate to your Cosmos DB account
3. Open Data Explorer
4. Browse to `InformationExtractionDB` > `ProcessedDocuments`

### Sample Output Document Structure

```json
{
  "id": "sample.txt_2024-01-15T10:30:00.000Z",
  "originalFileName": "sample.txt",
  "blobSize": 1024,
  "processedTimestamp": "2024-01-15T10:30:00.000Z",
  "extractedText": "Content of the document...",
  "metadata": {
    "fileExtension": "txt",
    "fileSizeBytes": 1024,
    "wordCount": 156,
    "characterCount": 1024,
    "processingMethod": "basic_text_extraction"
  },
  "processingStatus": "completed"
}
```

## Local Development

### Setup

1. Install Python 3.11
2. Install Azure Functions Core Tools
3. Install dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

Update `local.settings.json` with your Azure resources:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=<storage-account>;AccountKey=<key>;EndpointSuffix=core.windows.net",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "COSMOS_DB_ENDPOINT": "https://<cosmos-account>.documents.azure.com:443/",
    "COSMOS_DB_DATABASE_NAME": "InformationExtractionDB",
    "COSMOS_DB_CONTAINER_NAME": "ProcessedDocuments"
  }
}
```

### Run Locally

```bash
func start
```

## Extending the Solution

### Add More Document Types

Modify `process_document()` function to handle additional file types:

```python
# Example: Add PDF processing
if filename.lower().endswith('.pdf'):
    import PyPDF2
    # PDF processing logic here
```

### Enhanced Text Processing

Integrate with Azure Cognitive Services for advanced text analysis:
- Text Analytics for sentiment, key phrases, entities
- Form Recognizer for structured document processing
- Computer Vision for image and handwriting recognition

### Custom Processing Logic

Add domain-specific processing logic based on your use case:
- Invoice processing
- Resume parsing  
- Document classification
- Data validation

## Monitoring

The solution includes:
- Function App logs in Application Insights
- Cosmos DB metrics and logs
- Storage Account activity logs

Access logs through:
- Azure Portal > Function App > Monitor
- Azure Portal > Application Insights
- Azure Monitor workbooks

## Security

The solution uses:
- System-assigned managed identity for authentication
- Role-based access control (RBAC)
- HTTPS-only communication
- Minimal required permissions

## Cost Optimization

- Consumption plan for Functions (pay-per-execution)
- Standard storage tier
- Cosmos DB provisioned throughput (400 RU/s)
- Consider Cosmos DB serverless for variable workloads

## Support

For issues and questions:
1. Check the Function App logs in Application Insights
2. Verify role assignments and permissions
3. Ensure storage account and Cosmos DB connectivity
