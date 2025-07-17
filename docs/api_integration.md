# API Integration Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [RAG API Overview](#rag-api-overview)
3. [Authentication](#authentication)
4. [Integration Points](#integration-points)
5. [Document Upload](#document-upload)
6. [Media Handling](#media-handling)
7. [Domain Classification](#domain-classification)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [API Client Implementation](#api-client-implementation)
11. [Testing and Validation](#testing-and-validation)

## Introduction

This document provides detailed information on integrating the Production Web Scraper with the Farmovation RAG API and other external systems. The scraper is designed with a modular architecture that allows for easy integration with various APIs and storage systems.

## RAG API Overview

The Farmovation RAG API is a comprehensive REST API for agricultural knowledge retrieval and management. It provides intelligent document search and storage across 8 specialized agricultural domains using state-of-the-art vector embeddings and semantic search capabilities.

### Base URLs

- **Production**: `http://217.154.66.145:8000`
- **Development**: `http://localhost:8000`

### Available Domains

| Domain | Port | Description | Collection Name |
|--------|------|-------------|-----------------|
| `agriculture` | 6333 | General farming knowledge | `agriculture_general` |
| `water` | 6334 | Water management systems | `water_management` |
| `weather` | 6335 | Weather intelligence | `weather_intelligence` |
| `crops` | 6336 | Crop health monitoring | `crop_health` |
| `farm` | 6337 | Farm operations | `farm_operations` |
| `marketplace` | 6338 | Agricultural marketplace | `agricultural_marketplace` |
| `banking` | 6339 | Banking & insurance | `banking_insurance` |
| `chat` | 6340 | Conversation memory | `chat_memory` |

## Authentication

### API Key Format

The RAG API uses API keys in the following format:

```
ragnar_{32_character_base64_token}
```

Example: `ragnar_x7K9mL3nR8pQ2vF6sA1cE5wY4uI0tH9gB7jD6kM8xZ3`

### Authentication Flow

1. **Set API Key Environment Variable**:
   ```bash
   set RAG_API_KEY=your_api_key_here  # Windows
   # OR
   export RAG_API_KEY=your_api_key_here  # macOS/Linux
   ```

2. **API Key in HTTP Headers**:
   The scraper automatically includes the API key in the Authorization header:
   ```
   Authorization: Bearer ragnar_{32_character_token}
   ```

### API Key Management

- API keys are managed by the RAG API administrators
- Keys can be revoked or rotated as needed
- Each key has usage tracking and metadata

## Integration Points

The Production Web Scraper integrates with the RAG API at several points:

### 1. Document Upload

- Single document upload to specific domains
- Batch document upload for efficiency
- Document metadata management

### 2. Domain Management

- Domain information retrieval
- Collection statistics

### 3. Authentication

- API key validation
- Usage tracking

## Document Upload

### Single Document Upload

The scraper uploads documents to the RAG API using the following endpoint:

```
POST /api/v1/documents/{domain}
```

#### Request Format

```json
{
  "text": "Markdown content goes here...",
  "metadata": {
    "title": "Document Title",
    "url": "https://source-url.com",
    "timestamp": "2023-07-17T12:34:56Z",
    "content_hash": "hash_value",
    "processing_time": 1.23,
    "retry_count": 0,
    "media_count": 5,
    "original_metadata": {
      "additional": "metadata",
      "from": "source"
    }
  }
}
```

#### Response Format

```json
{
  "document_id": "uuid4-generated-id",
  "status": "success",
  "message": "Document added successfully",
  "domain": "agriculture",
  "embedding_dimension": 384,
  "processing_time_ms": 45.2
}
```

### Batch Document Upload

For efficiency, the scraper can upload multiple documents in a single request:

```
POST /api/v1/documents/{domain}/batch
```

#### Request Format

```json
[
  {
    "text": "First document content...",
    "metadata": { ... }
  },
  {
    "text": "Second document content...",
    "metadata": { ... }
  }
]
```

#### Response Format

```json
{
  "document_ids": ["id1", "id2"],
  "status": "success",
  "message": "2 documents added successfully",
  "domain": "agriculture",
  "processing_time_ms": 120.5
}
```

## Media Handling

The RAG API does not directly store media files. Instead, the scraper:

1. Extracts media URLs and metadata
2. Downloads media files to local storage
3. Creates a media catalog with references
4. Includes media references in document metadata

### Media Catalog Format

```json
{
  "url": "https://source-url.com",
  "timestamp": "2023-07-17T12:34:56Z",
  "media_items": [
    {
      "type": "image",
      "url": "https://example.com/image.jpg",
      "alt_text": "Description of image",
      "local_path": "files/images/image.jpg",
      "size": 12345
    },
    {
      "type": "pdf",
      "url": "https://example.com/document.pdf",
      "local_path": "files/documents/document.pdf",
      "size": 67890
    }
  ]
}
```

## Domain Classification

### Classification Process

The scraper classifies content into domains using keyword matching:

1. Extract text content from the crawled page
2. Compare content against domain keywords
3. Calculate relevance score for each domain
4. Assign content to domains with scores above threshold
5. Default to 'agriculture' domain if no clear match

### Domain Keywords

Domain keywords are defined in the configuration file:

```yaml
domains:
  agriculture: ["farm", "crop", "soil", "organic", "agriculture"]
  water: ["irrigation", "water", "drainage", "hydro"]
  # Other domains...
```

### Multi-Domain Assignment

Content can be assigned to multiple domains if it's relevant to multiple areas. The scraper will upload the document to each relevant domain.

## Error Handling

### Error Categories

The scraper handles various API integration errors:

1. **Authentication Errors** (401 Unauthorized)
   - Invalid API key
   - Expired API key
   - Missing API key

2. **Permission Errors** (403 Forbidden)
   - Insufficient permissions
   - IP address restrictions

3. **Rate Limiting** (429 Too Many Requests)
   - Exceeded API rate limits

4. **Server Errors** (500 Internal Server Error)
   - Temporary API unavailability
   - Backend processing errors

### Error Recovery

The scraper implements robust error recovery strategies:

1. **Exponential Backoff**
   - Initial retry after 1 second
   - Double delay for each retry (1s, 2s, 4s, 8s...)
   - Maximum delay of 60 seconds
   - Random jitter to prevent thundering herd

2. **Circuit Breaker**
   - Detect persistent API failures
   - Temporarily stop requests to failing endpoints
   - Periodically test if API has recovered

3. **Fallback to Local Storage**
   - If API upload fails after retries, save locally
   - Allow manual upload later

## Rate Limiting

### API Rate Limits

The RAG API implements rate limiting to prevent abuse:

- 10 requests per minute per API key
- 429 status code when limit exceeded
- Retry-After header indicates wait time

### Rate Limit Handling

The scraper handles rate limits automatically:

1. Tracks request timestamps
2. Respects Retry-After headers
3. Implements client-side rate limiting
4. Adds exponential backoff for 429 responses

## API Client Implementation

The scraper's RAG API client is implemented in `scraper/storage/rag_uploader.py`. Key components include:

### Session Management

```python
# Create HTTP session with API key authentication
timeout = aiohttp.ClientTimeout(total=30)
headers = {
    'User-Agent': 'Production-Web-Scraper/1.0',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {self.api_key}'
}
self.session = aiohttp.ClientSession(
    timeout=timeout,
    headers=headers
)
```

### Document Upload

```python
async def upload_document(self, document: ScrapedDocument, domain: str) -> str:
    """
    Upload single document to RAG API
    
    Args:
        document: Document to upload
        domain: Target domain
        
    Returns:
        Document ID from API
    """
    # Prepare document data
    doc_data = {
        'text': document.markdown,
        'metadata': {
            'title': document.title,
            'url': document.url,
            # Other metadata...
        }
    }
    
    # Upload with retry logic
    endpoint = self.domain_endpoints[domain]
    upload_url = f"{self.api_url}{endpoint}"
    
    async with self.session.post(upload_url, json=doc_data) as response:
        if response.status in [200, 201]:
            result = await response.json()
            return result.get('document_id')
        # Error handling...
```

### Batch Upload

```python
async def upload_batch(self, documents: List[ScrapedDocument], domain: str) -> List[str]:
    """
    Upload multiple documents to RAG API
    
    Args:
        documents: List of documents to upload
        domain: Target domain
        
    Returns:
        List of document IDs
    """
    # Prepare batch data
    batch_data = []
    for document in documents:
        doc_data = {
            'text': document.markdown,
            'metadata': {
                # Metadata fields...
            }
        }
        batch_data.append(doc_data)
    
    # Upload batch
    endpoint = f"{self.domain_endpoints[domain]}/batch"
    upload_url = f"{self.api_url}{endpoint}"
    
    async with self.session.post(upload_url, json=batch_data) as response:
        if response.status in [200, 201]:
            result = await response.json()
            return result.get('document_ids', [])
        # Error handling...
```

## Testing and Validation

### API Connectivity Test

The scraper tests API connectivity during initialization:

```python
async def _test_api_connectivity(self) -> bool:
    """
    Test API connectivity and authentication
    
    Returns:
        True if API is accessible and authentication works
    """
    try:
        # Test with the health endpoint
        test_url = f"{self.api_url}/health"
        
        async with self.session.get(test_url) as response:
            if response.status in [200, 201]:
                # Now test an authenticated endpoint
                auth_test_url = f"{self.api_url}/auth/me"
                
                async with self.session.get(auth_test_url) as auth_response:
                    if auth_response.status in [200, 201]:
                        return True
                    # Error handling...
    except Exception as e:
        # Error handling...
```

### Manual API Testing

You can test the RAG API manually using curl:

```bash
# Set API key
set API_KEY=your_api_key_here

# Test authentication
curl -H "Authorization: Bearer %API_KEY%" http://217.154.66.145:8000/auth/me

# Test document upload
curl -X POST "http://217.154.66.145:8000/api/v1/documents/agriculture" ^
  -H "Authorization: Bearer %API_KEY%" ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Test document\", \"metadata\": {\"source\": \"test\"}}"
```

### Integration Test Script

A test script is provided to validate API integration:

```bash
python -m scraper.tests.test_rag_integration
```

This script tests:
- API connectivity
- Authentication
- Document upload
- Batch upload
- Error handling
- Rate limiting