"""
Schema management utilities for Azure AI Content Understanding.
"""
import json
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

class SchemaManager:
    """Manages document extraction schemas for Azure AI Content Understanding."""
    
    def __init__(self, schemas_directory: str = None):
        """
        Initialize the schema manager.
        
        Args:
            schemas_directory: Path to the directory containing schema files
        """
        if schemas_directory is None:
            # Default to schemas directory relative to the project root
            current_dir = Path(__file__).parent.parent  # Go up one level from utils
            schemas_directory = current_dir / "schemas"
        
        self.schemas_directory = Path(schemas_directory)
        self._schema_cache = {}
        
    def load_schema(self, schema_name: str, version: str = "v1") -> Dict[str, Any]:
        """
        Load a schema from the schemas directory.
        
        Args:
            schema_name: Base name of the schema (e.g., 'document_schema')
            version: Version of the schema (e.g., 'v1')
            
        Returns:
            Dictionary containing the schema definition
        """
        cache_key = f"{schema_name}_{version}"
        
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]
        
        schema_file = self.schemas_directory / f"{schema_name}_{version}.json"
        
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            self._schema_cache[cache_key] = schema
            logging.info(f"Loaded schema: {schema_name} version {version}")
            return schema
            
        except FileNotFoundError:
            logging.error(f"Schema file not found: {schema_file}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in schema file {schema_file}: {e}")
            raise
    
    def get_default_schema(self) -> Dict[str, Any]:
        """
        Get the default document extraction schema.
        
        Returns:
            Dictionary containing the default schema definition
        """
        return self.load_schema("document_schema", "v1")
    
    def list_available_schemas(self) -> list:
        """
        List all available schemas in the schemas directory.
        
        Returns:
            List of tuples (schema_name, version)
        """
        schemas = []
        
        if not self.schemas_directory.exists():
            return schemas
        
        for schema_file in self.schemas_directory.glob("*.json"):
            # Parse filename: schema_name_version.json
            name_parts = schema_file.stem.split('_')
            if len(name_parts) >= 2:
                version = name_parts[-1]
                schema_name = '_'.join(name_parts[:-1])
                schemas.append((schema_name, version))
        
        return schemas
    
    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Basic validation of a schema structure.
        
        Args:
            schema: Schema dictionary to validate
            
        Returns:
            True if schema appears valid, False otherwise
        """
        required_keys = ['name', 'fields']
        
        if not all(key in schema for key in required_keys):
            logging.error(f"Schema missing required keys: {required_keys}")
            return False
        
        if not isinstance(schema['fields'], list):
            logging.error("Schema 'fields' must be a list")
            return False
        
        # Validate each field
        for field in schema['fields']:
            if not isinstance(field, dict):
                logging.error("Each field must be a dictionary")
                return False
            
            if 'name' not in field or 'type' not in field:
                logging.error("Each field must have 'name' and 'type' properties")
                return False
        
        logging.info(f"Schema '{schema.get('name')}' validation passed")
        return True

# Global schema manager instance
schema_manager = SchemaManager()
