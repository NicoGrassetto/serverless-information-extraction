"""
Azure AI Content Understanding client for document processing.
"""
import os
import json
import logging
import requests
import base64
from typing import Dict, Any, Optional, Union
from datetime import datetime

class AIContentUnderstandingClient:
    """Client for Azure AI Content Understanding service."""
    
    def __init__(self):
        """Initialize the client with configuration from environment variables."""
        self.endpoint = os.environ.get("AI_CONTENT_UNDERSTANDING_ENDPOINT", "").rstrip("/")
        self.api_key = os.environ.get("AI_CONTENT_UNDERSTANDING_KEY", "")
        self.region = os.environ.get("AI_CONTENT_UNDERSTANDING_REGION", "")
        
        if not self.endpoint or not self.api_key:
            raise ValueError("AI_CONTENT_UNDERSTANDING_ENDPOINT and AI_CONTENT_UNDERSTANDING_KEY must be set")
        
        self.api_version = "2024-11-15-preview"  # Update this based on latest available version
        self._schema_cache = {}
        
    def register_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a schema with Azure AI Content Understanding.
        
        Args:
            schema: Schema definition dictionary
            
        Returns:
            Dictionary containing schema registration response with id and version
        """
        url = f"{self.endpoint}/authoring/schemas"
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        params = {
            "api-version": self.api_version
        }
        
        try:
            logging.info(f"Registering schema: {schema.get('name', 'unnamed')}")
            
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=schema,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Cache the schema info
            schema_key = f"{schema.get('name')}_{schema.get('version', '1.0')}"
            self._schema_cache[schema_key] = result
            
            logging.info(f"Successfully registered schema: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to register schema: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            raise
    
    def analyze_document(self, 
                        document_content: bytes, 
                        filename: str,
                        schema_id: str,
                        schema_version: Optional[str] = None,
                        content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a document using Azure AI Content Understanding.
        
        Args:
            document_content: Raw bytes of the document
            filename: Name of the document file
            schema_id: ID of the registered schema to use
            schema_version: Version of the schema (optional)
            content_type: MIME type of the document (auto-detected if not provided)
            
        Returns:
            Dictionary containing analysis results
        """
        url = f"{self.endpoint}/analyze"
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        params = {
            "api-version": self.api_version
        }
        
        # Auto-detect content type if not provided
        if content_type is None:
            content_type = self._detect_content_type(filename)
        
        # Encode document content as base64
        document_b64 = base64.b64encode(document_content).decode('utf-8')
        
        # Prepare the request payload
        payload = {
            "schemaId": schema_id,
            "documents": [
                {
                    "documentId": f"{filename}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "contentType": content_type,
                    "content": document_b64
                }
            ]
        }
        
        if schema_version:
            payload["schemaVersion"] = schema_version
        
        try:
            logging.info(f"Analyzing document: {filename} with schema: {schema_id}")
            
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=120  # Document analysis can take longer
            )
            
            response.raise_for_status()
            result = response.json()
            
            logging.info(f"Successfully analyzed document: {filename}")
            return result
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to analyze document {filename}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            raise
    
    def _detect_content_type(self, filename: str) -> str:
        """
        Detect content type based on file extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            MIME type string
        """
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        content_type_map = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'json': 'application/json',
            'xml': 'application/xml',
            'html': 'text/html',
            'htm': 'text/html',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'tif': 'image/tiff'
        }
        
        return content_type_map.get(ext, 'application/octet-stream')
    
    def get_schema_info(self, schema_name: str, schema_version: str) -> Optional[Dict[str, Any]]:
        """
        Get cached schema information.
        
        Args:
            schema_name: Name of the schema
            schema_version: Version of the schema
            
        Returns:
            Schema info dictionary or None if not found
        """
        schema_key = f"{schema_name}_{schema_version}"
        return self._schema_cache.get(schema_key)
    
    def list_schemas(self) -> Dict[str, Any]:
        """
        List all registered schemas.
        
        Returns:
            Dictionary containing list of schemas
        """
        url = f"{self.endpoint}/authoring/schemas"
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }
        
        params = {
            "api-version": self.api_version
        }
        
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to list schemas: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            raise
