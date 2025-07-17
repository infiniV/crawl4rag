# Farmovation RAG API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Security & Authentication](#security--authentication)
4. [API Endpoints](#api-endpoints)
5. [Domain Management](#domain-management)
6. [Docker Volume Management](#docker-volume-management)
7. [Getting Started](#getting-started)
8. [Testing](#testing)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Overview

The Farmovation RAG API is a comprehensive REST API for agricultural knowledge retrieval and management. It provides intelligent document search and storage across 8 specialized agricultural domains using state-of-the-art vector embeddings and semantic search capabilities.

### Key Features

- 🌱 **8 Agricultural Domains**: Specialized knowledge bases for different agricultural sectors
- 🔍 **Semantic Search**: Advanced natural language querying with sub-30ms response times
- 📄 **Document Management**: Store, index, and retrieve agricultural documents with metadata
- 🔐 **Secure Authentication**: API key-based authentication with usage tracking
- 📊 **OpenAPI Compliance**: Full Swagger/OpenAPI 3.1.0 specification
- 🐳 **Docker Integration**: Containerized deployment with persistent volume storage
- ⚡ **High Performance**: FastAPI framework with async operations

### Technical Specifications

- **API Framework**: FastAPI with OpenAPI 3.1.0
- **Vector Database**: Qdrant v1.14.1 with COSINE similarity
- **Embeddings**: FastEmbed with sentence-transformers/all-MiniLM-L6-v2
- **Vector Dimensions**: 384
- **Response Format**: JSON
- **Authentication**: HTTP Bearer tokens

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Client App    │────│  Farmovation     │────│    8 x Qdrant       │
│                 │    │   RAG API        │    │   Vector Stores     │
│  - Web Apps     │    │                  │    │                     │
│  - Mobile Apps  │    │  - FastAPI       │    │ - Agriculture (6333)│
│  - Scripts      │    │  - Authentication│    │ - Water (6334)      │
│                 │    │  - Document Mgmt │    │ - Weather (6335)    │
└─────────────────┘    │  - Search Engine │    │ - Crops (6336)      │
                       │  - OpenAPI Docs  │    │ - Farm (6337)       │
                       └──────────────────┘    │ - Marketplace (6338)│
                                               │ - Banking (6339)    │
                                               │ - Chat (6340)       │
                                               └─────────────────────┘
```

### Domain Architecture

Each agricultural domain operates independently with its own:

- **Vector Database**: Dedicated Qdrant instance
- **Collection**: Domain-specific document collection
- **Port**: Unique port for external access
- **Configuration**: Specialized settings and parameters

## Security & Authentication

### 🏠 Localhost-Only Admin Security

**Maximum Security Architecture**: Critical administrative operations are restricted to localhost access only, providing the highest level of security possible.

#### Protected Admin Operations

- **API Key Creation**: `POST /auth/create-key`
- **List All API Keys**: `GET /auth/keys`
- **Revoke Any API Key**: `DELETE /auth/keys/{key_id}`

#### Security Benefits

- **🚫 Remote Access Blocked**: Admin operations cannot be accessed remotely
- **🔐 Physical Security Required**: Requires SSH/console access to server
- **🛡️ Network Attack Prevention**: Eliminates network-based admin attacks
- **🎯 Zero Remote Attack Surface**: Even compromised credentials cannot be used remotely

#### Usage From Localhost

```bash
# ✅ This works from localhost (127.0.0.1, ::1)
curl -X POST "http://localhost:8000/auth/create-key" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ANY_VALID_API_KEY" \
  -d '{"name": "new-user", "description": "User API key"}'

# ❌ This is blocked from remote IPs
curl -X POST "http://217.154.66.145:8000/auth/create-key" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_API_KEY" \
  -d '{"name": "new-user", "description": "User API key"}'
# Response: 403 Forbidden - Admin operations only allowed from localhost
```

### API Key Management

The API uses a secure file-based API key management system with the following features:

#### Security Features

- **Hashed Storage**: API keys are stored using SHA-256 hashing
- **Persistent Storage**: Keys stored in Docker shared volumes (`/app/data/api_keys/`)
- **Usage Tracking**: Automatic tracking of key usage and last access
- **Revocation**: Immediate key deactivation capability
- **Metadata**: Rich metadata including creation time, description, and usage stats

#### Authentication Flow

1. **API Key Creation**:

   ```bash
   POST /auth/create-key
   ```

   - Returns plaintext API key (shown only once)
   - Stores hashed version with metadata

2. **Request Authentication**:

   ```
   Authorization: Bearer ragnar_{32_character_token}
   ```

   - All protected endpoints require valid Bearer token
   - Invalid tokens return 401 Unauthorized

3. **Usage Tracking**:
   - Each API call increments usage counter
   - Updates last_used timestamp
   - Tracks per-key statistics

#### API Key Format

```
ragnar_{32_character_base64_token}
```

Example: `ragnar_x7K9mL3nR8pQ2vF6sA1cE5wY4uI0tH9gB7jD6kM8xZ3`

### File Storage Security

API keys are stored in `/app/data/api_keys/api_keys.json` with:

```json
{
  "hashed_key": {
    "id": "uuid4",
    "name": "key_name",
    "description": "key_description",
    "created_at": "ISO8601_timestamp",
    "last_used": "ISO8601_timestamp",
    "is_active": true,
    "usage_count": 42
  }
}
```

### Security Best Practices

1. **Key Rotation**: Regularly rotate API keys
2. **Environment Variables**: Store keys in environment variables, not code
3. **HTTPS Only**: Always use HTTPS in production
4. **Key Scope**: Use different keys for different applications
5. **Monitoring**: Monitor key usage patterns
6. **Revocation**: Immediately revoke compromised keys

## API Endpoints

### Base URL

- **Production**: `http://217.154.66.145:8000`
- **Development**: `http://localhost:8000`

### Endpoint Categories

#### 🔐 Authentication Endpoints

| Method | Endpoint              | Description         | Auth Required     |
| ------ | --------------------- | ------------------- | ----------------- |
| POST   | `/auth/create-key`    | Create new API key  | 🏠 Localhost Only |
| GET    | `/auth/keys`          | List all API keys   | 🏠 Localhost Only |
| DELETE | `/auth/keys/{key_id}` | Revoke API key      | 🏠 Localhost Only |
| GET    | `/auth/me`            | Get my API key info | ✅                |
| DELETE | `/auth/me`            | Revoke my API key   | ✅                |

#### 🏭 Domain Management

| Method | Endpoint                              | Description          | Auth Required |
| ------ | ------------------------------------- | -------------------- | ------------- |
| GET    | `/api/v1/domains`                     | List all domains     | ✅            |
| GET    | `/api/v1/domains/{domain}`            | Get domain info      | ✅            |
| GET    | `/api/v1/domains/{domain}/collection` | Get collection stats | ✅            |

#### 📄 Document Management

| Method | Endpoint                           | Description            | Auth Required |
| ------ | ---------------------------------- | ---------------------- | ------------- |
| POST   | `/api/v1/documents/{domain}`       | Add single document    | ✅            |
| POST   | `/api/v1/documents/{domain}/batch` | Add multiple documents | ✅            |

#### 🔍 Search Operations

| Method | Endpoint                  | Description             | Auth Required |
| ------ | ------------------------- | ----------------------- | ------------- |
| POST   | `/api/v1/search/{domain}` | Search single domain    | ✅            |
| POST   | `/api/v1/search`          | Search multiple domains | ✅            |

#### 🔢 Embedding Operations

| Method | Endpoint                  | Description         | Auth Required |
| ------ | ------------------------- | ------------------- | ------------- |
| POST   | `/api/v1/embeddings`      | Generate embeddings | ✅            |
| GET    | `/api/v1/embeddings/info` | Get model info      | ✅            |

#### ⚙️ System Information

| Method | Endpoint         | Description   | Auth Required |
| ------ | ---------------- | ------------- | ------------- |
| GET    | `/health`        | Health check  | ❌            |
| GET    | `/api/v1/status` | System status | ✅            |
| GET    | `/`              | Root endpoint | ❌            |

#### 📖 Documentation

| Method | Endpoint                       | Description           | Auth Required |
| ------ | ------------------------------ | --------------------- | ------------- |
| GET    | `/docs`                        | Swagger UI            | ❌            |
| GET    | `/redoc`                       | ReDoc documentation   | ❌            |
| GET    | `/openapi.json`                | OpenAPI schema        | ❌            |
| GET    | `/api/v1/docs/examples`        | API examples          | ❌            |
| GET    | `/api/v1/docs/getting-started` | Getting started guide | ❌            |
| GET    | `/api/v1/docs/domains`         | Domain documentation  | ❌            |

### Detailed Endpoint Documentation

#### Create API Key

```http
POST /auth/create-key
Content-Type: application/json

{
  "name": "my-application",
  "description": "API key for my farming app"
}
```

**Response:**

```json
{
  "api_key": "ragnar_x7K9mL3nR8pQ2vF6sA1cE5wY4uI0tH9gB7jD6kM8xZ3",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my-application",
  "description": "API key for my farming app",
  "created_at": "2024-01-15T10:30:00Z",
  "message": "Store this API key securely. It won't be shown again."
}
```

#### Add Document

```http
POST /api/v1/documents/agriculture
Authorization: Bearer ragnar_x7K9mL3nR8pQ2vF6sA1cE5wY4uI0tH9gB7jD6kM8xZ3
Content-Type: application/json

{
  "text": "Crop rotation is essential for sustainable farming. It helps prevent soil depletion and reduces pest buildup.",
  "metadata": {
    "source": "farming-guide",
    "type": "guide",
    "author": "Agricultural Expert",
    "tags": ["sustainability", "crop-rotation"]
  }
}
```

**Response:**

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

#### Search Documents

```http
POST /api/v1/search/agriculture
Authorization: Bearer ragnar_x7K9mL3nR8pQ2vF6sA1cE5wY4uI0tH9gB7jD6kM8xZ3
Content-Type: application/json

{
  "query": "sustainable farming techniques",
  "limit": 5,
  "similarity_threshold": 0.7
}
```

**Response:**

```json
{
  "query": "sustainable farming techniques",
  "domain": "agriculture",
  "results": [
    {
      "id": "document-uuid",
      "text": "Crop rotation is essential for sustainable farming...",
      "score": 0.89,
      "metadata": {
        "source": "farming-guide",
        "type": "guide"
      }
    }
  ],
  "total_results": 1,
  "processing_time_ms": 23.4,
  "embedding_time_ms": 12.1,
  "search_time_ms": 11.3
}
```

## Domain Management

### Available Domains

| Domain        | Port | Description               | Collection Name            |
| ------------- | ---- | ------------------------- | -------------------------- |
| `agriculture` | 6333 | General farming knowledge | `agriculture_general`      |
| `water`       | 6334 | Water management systems  | `water_management`         |
| `weather`     | 6335 | Weather intelligence      | `weather_intelligence`     |
| `crops`       | 6336 | Crop health monitoring    | `crop_health`              |
| `farm`        | 6337 | Farm operations           | `farm_operations`          |
| `marketplace` | 6338 | Agricultural marketplace  | `agricultural_marketplace` |
| `banking`     | 6339 | Banking & insurance       | `banking_insurance`        |
| `chat`        | 6340 | Conversation memory       | `chat_memory`              |

### Domain Selection Guide

**Choose the right domain for your use case:**

- **Agriculture**: General farming practices, soil management, organic farming
- **Water**: Irrigation systems, water conservation, drainage solutions
- **Weather**: Seasonal planning, climate data, weather risk assessment
- **Crops**: Disease identification, pest control, crop nutrition
- **Farm**: Equipment maintenance, operations planning, logistics
- **Marketplace**: Commodity prices, market trends, trading strategies
- **Banking**: Farm loans, insurance, financial planning
- **Chat**: Conversation history, user preferences, session data

## Docker Volume Management

### Volume Structure

The API uses Docker shared volumes for persistent data storage:

```
/app/data/
├── api_keys/
│   └── api_keys.json          # API key storage
├── documents/                 # Document categories
│   ├── agriculture/
│   ├── water/
│   ├── weather/
│   ├── crops/
│   ├── farm_management/
│   ├── marketplace/
│   ├── banking/
│   └── water_management/
├── processed/                 # Processed documents
├── embeddings_cache/          # Embedding cache
└── uploads/                   # Upload staging
    ├── completed/
    ├── failed/
    ├── pending/
    └── processing/
```

### Volume Configuration in docker-compose.yml

```yaml
volumes:
  # Mount entire project for development
  - .:/app
  # Document storage
  - ./data/documents:/app/data/documents
  - ./data/processed:/app/data/processed
  - ./data/embeddings_cache:/app/data/embeddings_cache
  - ./data/uploads:/app/data/uploads
  # Logs
  - ragnar-logs:/app/logs
```

### API Key Storage

API keys are stored in `/app/data/api_keys/api_keys.json` which maps to `./data/api_keys/api_keys.json` on the host system.

**File Permissions:**

- Directory: `777` (rwxrwxrwx)
- File: `644` (rw-r--r--)

**Backup Recommendations:**

1. Regular backup of `api_keys.json`
2. Store backups securely (encrypted)
3. Test restoration procedures
4. Version control excluding sensitive data

## Getting Started

### 1. Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- curl or HTTP client for testing

### 2. Start the Services

```bash
# Clone repository
git clone https://github.com/Farmovation/Farmovation-RAG.git
cd Farmovation-RAG

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 3. Create Your First API Key

```bash
# Using the management script
./scripts/manage_api_keys.sh create my-app "My farming application"

# Or using curl directly
curl -X POST "http://localhost:8000/auth/create-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "description": "My farming application"}'
```

### 4. Test the API

```bash
# Run quick test
./tests/quick_test.sh http://localhost:8000

# Run comprehensive test suite
./tests/api_test_suite.sh http://localhost:8000
```

### 5. Add Your First Document

```bash
export API_KEY="your-api-key-here"

curl -X POST "http://localhost:8000/api/v1/documents/agriculture" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Organic farming practices improve soil health and biodiversity.",
    "metadata": {
      "source": "organic-farming-guide",
      "type": "guide"
    }
  }'
```

### 6. Search Documents

```bash
curl -X POST "http://localhost:8000/api/v1/search/agriculture" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "organic farming",
    "limit": 5
  }'
```

## Testing

### Automated Test Suite

Run the comprehensive test suite:

```bash
# Test production server
./tests/api_test_suite.sh http://217.154.66.145:8000

# Test local development
./tests/api_test_suite.sh http://localhost:8000

# Quick validation test
./tests/quick_test.sh
```

### Test Coverage

The test suite covers:

- ✅ Health checks and system status
- ✅ API key creation and authentication
- ✅ Domain management and information
- ✅ Document addition (single and batch)
- ✅ Search operations (single and multi-domain)
- ✅ Embedding generation
- ✅ Documentation endpoints
- ✅ Performance validation
- ✅ Error handling

### Manual Testing

Use the interactive Swagger UI at `/docs` for manual testing:

1. Visit `http://localhost:8000/docs`
2. Create an API key using the `/auth/create-key` endpoint
3. Click "Authorize" and enter your API key
4. Test any endpoint with the "Try it out" functionality

## Best Practices

### API Usage

1. **Rate Limiting**: Respect API rate limits and implement exponential backoff
2. **Error Handling**: Always handle HTTP status codes properly
3. **Timeout Handling**: Set appropriate request timeouts (30-60 seconds)
4. **Retry Logic**: Implement retry logic for transient failures
5. **Caching**: Cache responses when appropriate to reduce API calls

### Document Management

1. **Metadata**: Always include rich metadata for better searchability
2. **Text Quality**: Ensure document text is clean and well-formatted
3. **Domain Selection**: Choose the most specific domain for your content
4. **Batch Operations**: Use batch endpoints for multiple documents
5. **Size Limits**: Keep documents under 100MB for optimal performance

### Search Optimization

1. **Query Design**: Use natural language queries for best results
2. **Similarity Thresholds**: Adjust thresholds based on your use case
3. **Result Limits**: Request only the number of results you need
4. **Multi-Domain**: Use multi-domain search for comprehensive results
5. **Performance**: Monitor search response times and optimize queries

### Security

1. **Key Management**: Store API keys securely (environment variables)
2. **Key Rotation**: Regularly rotate API keys
3. **Access Control**: Use different keys for different applications
4. **HTTPS**: Always use HTTPS in production
5. **Monitoring**: Monitor API usage and detect anomalies

## Troubleshooting

### Common Issues

#### 1. Authentication Errors

**Problem**: `401 Unauthorized` responses

**Solutions**:

```bash
# Check API key format
echo $API_KEY | grep "^ragnar_"

# Verify key exists
./scripts/manage_api_keys.sh list

# Test with curl
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/v1/domains
```

#### 2. Connection Errors

**Problem**: `Connection refused` or `Service unavailable`

**Solutions**:

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs ragnar-server

# Restart services
docker-compose restart
```

#### 3. Document Addition Failures

**Problem**: Documents not being added successfully

**Solutions**:

```bash
# Check Qdrant services
docker-compose ps | grep qdrant

# Verify domain exists
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/v1/domains

# Check document format
# Ensure JSON is valid and text field is not empty
```

#### 4. Search Performance Issues

**Problem**: Slow search responses

**Solutions**:

```bash
# Check system resources
docker stats

# Optimize query
# Use specific domains instead of multi-domain search
# Reduce result limits
# Adjust similarity thresholds

# Check embedding performance
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"texts":["test"]}' \
  http://localhost:8000/api/v1/embeddings
```

### Log Analysis

```bash
# API server logs
docker logs ragnar-server

# Qdrant logs (example for agriculture)
docker logs qdrant-agri

# Follow logs in real-time
docker-compose logs -f
```

### Performance Monitoring

```bash
# System resource usage
docker stats

# API response times
time curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/v1/status

# Database connections
./tests/api_test_suite.sh | grep "Performance"
```

### Support

For additional support:

1. **Documentation**: Check `/docs` endpoint for interactive documentation
2. **Examples**: Visit `/api/v1/docs/examples` for comprehensive examples
3. **GitHub Issues**: Report bugs and feature requests on GitHub
4. **Test Suite**: Run the test suite to validate your environment

---

_This documentation is automatically updated with each API release. For the latest version, visit the API documentation endpoints._