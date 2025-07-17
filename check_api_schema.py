#!/usr/bin/env python3
"""
Check RAG API schema to understand the correct request format
"""

import asyncio
import aiohttp
import json


async def check_api_schema():
    """Check the RAG API OpenAPI schema to understand request format"""
    api_key = "ragnar_pzt3-FWkRbYxISfGVKqZnzpD_qDpZxxZLaTQGVdp_H4"
    # Use the VectorDB endpoint (port 8015)
    base_url = "http://217.154.66.145:8015"
    
    timeout = aiohttp.ClientTimeout(total=10)
    headers = {'Authorization': f'Bearer {api_key}'}
    
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        print("=== Checking RAG API Schema ===\n")
        
        # Get OpenAPI schema
        try:
            async with session.get(f"{base_url}/openapi.json") as response:
                if response.status == 200:
                    spec = await response.json()
                    
                    # Look for document upload endpoints
                    paths = spec.get('paths', {})
                    
                    print("📋 Document Upload Endpoints:")
                    print("-" * 50)
                    
                    for path, methods in paths.items():
                        if 'documents' in path and ('post' in methods):
                            print(f"\n🔗 {path}")
                            post_spec = methods['post']
                            
                            # Check request body schema
                            if 'requestBody' in post_spec:
                                request_body = post_spec['requestBody']
                                content = request_body.get('content', {})
                                
                                if 'application/json' in content:
                                    schema = content['application/json'].get('schema', {})
                                    print(f"   Request Schema:")
                                    
                                    if '$ref' in schema:
                                        # Resolve reference
                                        ref_path = schema['$ref'].split('/')[-1]
                                        components = spec.get('components', {})
                                        schemas = components.get('schemas', {})
                                        if ref_path in schemas:
                                            resolved_schema = schemas[ref_path]
                                            print_schema(resolved_schema, "     ")
                                    else:
                                        print_schema(schema, "     ")
                            
                            # Check response schema
                            if 'responses' in post_spec:
                                responses = post_spec['responses']
                                if '200' in responses or '201' in responses:
                                    success_response = responses.get('201', responses.get('200'))
                                    print(f"   Success Response: {success_response.get('description', 'N/A')}")
                    
                    # Look for specific schemas
                    print("\n📝 Relevant Schemas:")
                    print("-" * 50)
                    
                    components = spec.get('components', {})
                    schemas = components.get('schemas', {})
                    
                    relevant_schemas = [
                        'DocumentCreate', 'DocumentUpload', 'Document', 
                        'CreateDocument', 'UploadDocument', 'DocumentRequest'
                    ]
                    
                    for schema_name in relevant_schemas:
                        if schema_name in schemas:
                            print(f"\n📄 {schema_name}:")
                            print_schema(schemas[schema_name], "   ")
                    
                    # Look for any schema with 'text' or 'content' fields
                    print("\n🔍 Schemas with text/content fields:")
                    print("-" * 50)
                    
                    for schema_name, schema_def in schemas.items():
                        if 'properties' in schema_def:
                            props = schema_def['properties']
                            if 'text' in props or 'content' in props:
                                print(f"\n📄 {schema_name}:")
                                print_schema(schema_def, "   ")
                
                else:
                    print(f"Failed to get OpenAPI spec: {response.status}")
                    
        except Exception as e:
            print(f"Error getting API schema: {e}")
        
        # Test actual POST request to see what's expected
        print("\n🧪 Testing POST Request Format:")
        print("-" * 50)
        
        test_data_formats = [
            {
                "name": "Format 1: text field",
                "data": {
                    "title": "Test Document",
                    "text": "This is test content",
                    "url": "https://example.com/test"
                }
            },
            {
                "name": "Format 2: content field", 
                "data": {
                    "title": "Test Document",
                    "content": "This is test content",
                    "url": "https://example.com/test"
                }
            },
            {
                "name": "Format 3: with metadata",
                "data": {
                    "title": "Test Document",
                    "text": "This is test content",
                    "url": "https://example.com/test",
                    "metadata": {"source": "test"}
                }
            }
        ]
        
        for test_format in test_data_formats:
            print(f"\n🔬 Testing {test_format['name']}:")
            try:
                async with session.post(
                    f"{base_url}/api/v1/documents/agriculture", 
                    json=test_format['data']
                ) as response:
                    print(f"   Status: {response.status}")
                    if response.status in [200, 201]:
                        result = await response.json()
                        print(f"   ✅ Success: {result}")
                        break
                    else:
                        error = await response.text()
                        print(f"   ❌ Error: {error[:200]}...")
            except Exception as e:
                print(f"   ❌ Exception: {e}")


def print_schema(schema, indent=""):
    """Print schema in a readable format"""
    if 'properties' in schema:
        print(f"{indent}Properties:")
        for prop_name, prop_def in schema['properties'].items():
            prop_type = prop_def.get('type', 'unknown')
            required = prop_name in schema.get('required', [])
            req_marker = " (required)" if required else ""
            print(f"{indent}  - {prop_name}: {prop_type}{req_marker}")
            
            if 'description' in prop_def:
                print(f"{indent}    Description: {prop_def['description']}")
    
    if 'required' in schema:
        print(f"{indent}Required fields: {schema['required']}")
    
    if 'type' in schema and schema['type'] == 'array':
        print(f"{indent}Type: array")
        if 'items' in schema:
            print(f"{indent}Items:")
            print_schema(schema['items'], indent + "  ")


if __name__ == '__main__':
    asyncio.run(check_api_schema())