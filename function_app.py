import azure.functions as func
import logging
import json
import os
import datetime
import sys
from pathlib import Path

# Add the current directory to the path so we can import our utilities
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from utils.ai_content_understanding import AIContentUnderstandingClient
from utils.schema_manager import schema_manager

app = func.FunctionApp()

# Get configuration from environment variables
COSMOS_DB_ENDPOINT = os.environ.get("COSMOS_DB_ENDPOINT", "")
COSMOS_DB_DATABASE_NAME = os.environ.get("COSMOS_DB_DATABASE_NAME", "InformationExtractionDB")
COSMOS_DB_CONTAINER_NAME = os.environ.get("COSMOS_DB_CONTAINER_NAME", "ProcessedDocuments")

# Initialize AI Content Understanding client
ai_client = None
schema_id = None

def initialize_ai_client():
    """Initialize the AI Content Understanding client and register schema."""
    global ai_client, schema_id
    
    if ai_client is None:
        try:
            ai_client = AIContentUnderstandingClient()
            
            # Load and register the default schema
            schema = schema_manager.get_default_schema()
            
            # Check if schema is already registered (you might want to store this info)
            # For now, we'll attempt to register each time (consider caching this)
            try:
                schema_info = ai_client.register_schema(schema)
                schema_id = schema_info.get("id") or schema_info.get("schemaId")
                logging.info(f"Schema registered with ID: {schema_id}")
            except Exception as e:
                # If registration fails, we might already have it registered
                logging.warning(f"Schema registration failed (might already exist): {e}")
                # You could implement schema lookup logic here
                
        except Exception as e:
            logging.error(f"Failed to initialize AI Content Understanding client: {e}")
            raise


@app.blob_trigger(arg_name="myblob", path="documents/{name}",
                  connection="AzureWebJobsStorage")
@app.cosmos_db_output(arg_name="outputDocument", 
                      database_name=COSMOS_DB_DATABASE_NAME,
                      container_name=COSMOS_DB_CONTAINER_NAME,
                      connection="CosmosDbConnectionString")
def BlobTrigger(myblob: func.InputStream, outputDocument: func.Out[func.Document]) -> None:
    """
    Azure Function triggered by blob uploads to process documents using AI Content Understanding.
    
    This function is triggered when a new blob is uploaded to the 'documents' container.
    It processes the document using Azure AI Content Understanding and writes the results to Cosmos DB.
    """
    logging.info(f'Python blob trigger function processed blob '
                f'Name: {myblob.name} '
                f'Blob Size: {myblob.length} bytes')

    try:
        # Initialize AI client if not already done
        initialize_ai_client()
        
        if not ai_client or not schema_id:
            raise Exception("AI Content Understanding client not properly initialized")
        
        # Read the blob content
        blob_content = myblob.read()
        
        # Extract metadata from the blob
        blob_name = myblob.name.split('/')[-1]  # Get filename from full path
        blob_size = myblob.length
        
        # Process the document using AI Content Understanding
        extracted_info = process_document_with_ai(blob_content, blob_name)
        
        # Prepare document for Cosmos DB
        cosmos_document = {
            "id": f"{blob_name}_{extracted_info['timestamp'].replace(':', '-').replace('.', '-')}",
            "originalFileName": blob_name,
            "blobSize": blob_size,
            "processedTimestamp": extracted_info['timestamp'],
            "extractedData": extracted_info['extracted_data'],
            "metadata": extracted_info['metadata'],
            "processingStatus": "completed",
            "processingMethod": "azure_ai_content_understanding",
            "schemaVersion": extracted_info.get('schema_version', '1.0')
        }
        
        # Output to Cosmos DB
        outputDocument.set(func.Document.from_dict(cosmos_document))
        
        logging.info(f'Successfully processed document: {blob_name}')
        
    except Exception as e:
        logging.error(f'Error processing blob {myblob.name}: {str(e)}')
        
        # Create error document for Cosmos DB
        timestamp = datetime.datetime.utcnow().isoformat().replace(':', '-').replace('.', '-')
        error_document = {
            "id": f"{myblob.name.split('/')[-1]}_error_{timestamp}",
            "originalFileName": myblob.name.split('/')[-1],
            "blobSize": myblob.length,
            "processedTimestamp": datetime.datetime.utcnow().isoformat(),
            "error": str(e),
            "processingStatus": "error",
            "processingMethod": "azure_ai_content_understanding"
        }
        
        outputDocument.set(func.Document.from_dict(error_document))


def process_document_with_ai(blob_content: bytes, filename: str) -> dict:
    """
    Process the document content using Azure AI Content Understanding.
    
    Args:
        blob_content: The raw bytes of the uploaded file
        filename: The name of the uploaded file
        
    Returns:
        Dictionary containing extracted information
    """
    global ai_client, schema_id
    
    try:
        # Analyze document using AI Content Understanding
        result = ai_client.analyze_document(
            document_content=blob_content,
            filename=filename,
            schema_id=schema_id
        )
        
        # Extract the results from the AI response
        extracted_data = {}
        confidence_scores = {}
        
        if 'documents' in result and len(result['documents']) > 0:
            document_result = result['documents'][0]
            
            if 'fields' in document_result:
                fields = document_result['fields']
                
                # Process each field from the AI response
                for field_name, field_data in fields.items():
                    if isinstance(field_data, dict):
                        extracted_data[field_name] = field_data.get('value')
                        confidence_scores[field_name] = field_data.get('confidence', 0.0)
                    else:
                        extracted_data[field_name] = field_data
        
        # Extract basic file metadata
        file_extension = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
        file_size = len(blob_content)
        
        return {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "extracted_data": extracted_data,
            "confidence_scores": confidence_scores,
            "metadata": {
                "fileExtension": file_extension,
                "fileSizeBytes": file_size,
                "processingMethod": "azure_ai_content_understanding",
                "aiServiceResponse": result  # Store full response for debugging
            },
            "schema_version": "1.0"
        }
        
    except Exception as e:
        logging.error(f"AI processing failed for {filename}: {e}")
        
        # Fallback to basic processing if AI fails
        return process_document_fallback(blob_content, filename)


def process_document_fallback(blob_content: bytes, filename: str) -> dict:
    """
    Fallback document processing when AI Content Understanding fails.
    
    Args:
        blob_content: The raw bytes of the uploaded file
        filename: The name of the uploaded file
        
    Returns:
        Dictionary containing basic extracted information
    """
    try:
        # Try to decode as text (works for .txt, .csv, etc.)
        if filename.lower().endswith(('.txt', '.csv', '.json')):
            text_content = blob_content.decode('utf-8')
        else:
            # For other file types, we'll extract basic information
            text_content = f"Binary file: {filename}"
            
    except UnicodeDecodeError:
        text_content = f"Binary file that couldn't be decoded as text: {filename}"
    
    # Extract basic metadata
    file_extension = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
    file_size = len(blob_content)
    
    # Simple text analysis (word count, character count)
    word_count = len(text_content.split()) if isinstance(text_content, str) else 0
    char_count = len(text_content) if isinstance(text_content, str) else 0
    
    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "extracted_data": {
            "Summary": text_content[:1000] if len(text_content) > 1000 else text_content,
            "DocumentType": "other"
        },
        "confidence_scores": {},
        "metadata": {
            "fileExtension": file_extension,
            "fileSizeBytes": file_size,
            "wordCount": word_count,
            "characterCount": char_count,
            "processingMethod": "fallback_basic_extraction"
        },
        "schema_version": "fallback"
    }


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple health check endpoint for the Function App.
    """
    logging.info('Health check endpoint was called.')
    
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "message": "Information Extraction Function App is running"
        }),
        status_code=200,
        mimetype="application/json"
    )
