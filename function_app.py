import azure.functions as func
import logging
import json
import os
import datetime

app = func.FunctionApp()


@app.blob_trigger(arg_name="myblob", path="documents/{name}",
                  connection="AzureWebJobsStorage")
@app.cosmos_db_output(arg_name="outputDocument", 
                      database_name="InformationExtractionDB",
                      container_name="ProcessedDocuments",
                      connection="CosmosDbConnectionString")
def BlobTrigger(myblob: func.InputStream, outputDocument: func.Out[func.Document]) -> None:
    """
    Azure Function triggered by blob uploads to process documents.
    
    This function is triggered when a new blob is uploaded to the 'documents' container.
    It processes the document and writes the results to Cosmos DB using output binding.
    """
    logging.info(f'Python blob trigger function processed blob '
                f'Name: {myblob.name} '
                f'Blob Size: {myblob.length} bytes')

    try:
        # Read the blob content
        blob_content = myblob.read()
        
        # Extract metadata from the blob
        blob_name = myblob.name.split('/')[-1]  # Get filename from full path
        blob_size = myblob.length
        
        # Process the document (basic information extraction)
        extracted_info = process_document(blob_content, blob_name)
        
        # Prepare document for Cosmos DB
        cosmos_document = {
            "id": f"{blob_name}_{extracted_info['timestamp'].replace(':', '-').replace('.', '-')}",
            "originalFileName": blob_name,
            "blobSize": blob_size,
            "processedTimestamp": extracted_info['timestamp'],
            "extractedText": extracted_info['text'],
            "metadata": extracted_info['metadata'],
            "processingStatus": "completed"
        }
        
        # Set the output document using the output binding
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
            "processingStatus": "error"
        }
        
        # Set the error document using the output binding
        outputDocument.set(func.Document.from_dict(error_document))


def process_document(blob_content: bytes, filename: str) -> dict:
    """
    Process the document content and extract information.
    
    Args:
        blob_content: The raw bytes of the uploaded file
        filename: The name of the uploaded file
        
    Returns:
        Dictionary containing extracted information
    """
    
    # Basic text extraction (this is a simplified example)
    # In a real scenario, you might use OCR, PDF parsers, or other document processing libraries
    
    try:
        # Try to decode as text (works for .txt, .csv, etc.)
        if filename.lower().endswith(('.txt', '.csv', '.json')):
            text_content = blob_content.decode('utf-8')
        else:
            # For other file types, you might want to use specific libraries
            # For now, we'll extract basic information
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
        "text": text_content[:10000],  # Limit text to 10k characters for storage efficiency
        "metadata": {
            "fileExtension": file_extension,
            "fileSizeBytes": file_size,
            "wordCount": word_count,
            "characterCount": char_count,
            "processingMethod": "basic_text_extraction"
        }
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
