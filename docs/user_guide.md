# Production Web Scraper User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Command Line Options](#command-line-options)
5. [Configuration](#configuration)
6. [Operating Modes](#operating-modes)
7. [URL Management](#url-management)
8. [Content Processing](#content-processing)
9. [Media Extraction](#media-extraction)
10. [Domain Classification](#domain-classification)
11. [Performance Tuning](#performance-tuning)
12. [Logging and Monitoring](#logging-and-monitoring)
13. [Advanced Features](#advanced-features)

## Introduction

The Production Web Scraper is a comprehensive, scalable solution built on crawl4ai that performs deep website scanning and integrates with the Farmovation RAG API. The system is designed with a modular architecture supporting both production and development modes, concurrent processing, intelligent content categorization, and robust error handling.

### Key Features

- Deep website scanning with crawl4ai
- HTML to markdown conversion
- Media extraction and downloading
- Content classification for RAG domains
- Development and production modes
- Comprehensive logging and error handling
- Configurable via YAML/JSON and environment variables

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (optional, for cloning the repository)

### Installation Steps

1. Clone the repository (or download the source code):

```bash
git clone https://github.com/your-organization/production-web-scraper.git
cd production-web-scraper
```

2. Create and activate a virtual environment (recommended):

```bash
# On Windows
python -m venv .venv
.venv\Scripts\activate

# On macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Verify installation:

```bash
python -m scraper --version
```

## Basic Usage

### Development Mode (Default)

Development mode saves content to local folders without uploading to the RAG API:

```bash
python -m scraper --urls https://example.com
```

### Production Mode

Production mode uploads content directly to the RAG API:

```bash
# Set the API key as an environment variable
set RAG_API_KEY=your_api_key_here  # Windows
# OR
export RAG_API_KEY=your_api_key_here  # macOS/Linux

# Run in production mode
python -m scraper --mode=prod --urls https://example.com
```

### Using Default Agricultural URLs

The scraper comes with a predefined list of agricultural websites:

```bash
python -m scraper --use-default-urls
```

### Processing URLs from a File

```bash
python -m scraper --url-file=urls.txt
```

## Command Line Options

### Basic Options

| Option | Description | Default |
|--------|-------------|---------|
| `--mode` | Processing mode: `dev` or `prod` | `dev` |
| `--urls` | One or more URLs to process | None |
| `--url-file` | Path to file containing URLs | None |
| `--use-default-urls` | Use the default list of agricultural websites | False |
| `--config` | Path to configuration file | `config/config.yaml` |
| `--version` | Show version information and exit | N/A |
| `--examples` | Show usage examples and exit | N/A |

### Configuration Overrides

| Option | Description | Default |
|--------|-------------|---------|
| `--log-level` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | From config |
| `--max-workers` | Maximum number of concurrent workers | From config |
| `--max-depth` | Maximum crawl depth for following links | From config |
| `--rate-limit` | Rate limit in seconds between requests to the same domain | From config |
| `--timeout` | Request timeout in seconds | From config |

### Advanced Options

| Option | Description | Default |
|--------|-------------|---------|
| `--no-js` | Disable JavaScript execution during crawling | False |
| `--no-images` | Skip waiting for images during crawling | False |
| `--no-downloads` | Disable file downloads | False |

## Configuration

The scraper can be configured using a YAML or JSON configuration file. The default configuration file is located at `config/config.yaml`.

### Configuration Structure

```yaml
scraper:
  mode: "dev"  # dev or prod
  max_workers: 10
  max_depth: 3
  rate_limit: 1.0  # seconds between requests per domain
  timeout: 30
  
crawl4ai:
  headless: true
  wait_for_images: true
  scan_full_page: true
  scroll_delay: 0.5
  accept_downloads: true
  
storage:
  dev:
    base_path: "./docs"
    files_path: "./files"
  prod:
    rag_api_url: "http://217.154.66.145:8000"
    api_key_env: "RAG_API_KEY"
    
domains:
  agriculture: ["farm", "crop", "soil", "organic", "agriculture"]
  water: ["irrigation", "water", "drainage", "hydro"]
  weather: ["weather", "climate", "forecast", "meteorology"]
  crops: ["crop", "plant", "disease", "pest", "harvest"]
  farm: ["equipment", "machinery", "operation", "management"]
  marketplace: ["market", "price", "commodity", "trade"]
  banking: ["loan", "insurance", "finance", "credit"]
  chat: ["conversation", "chat", "dialogue", "interaction"]

logging:
  level: "INFO"
  file: "./logs/scraper.log"
  max_size: "100MB"
  backup_count: 5
```

### Environment Variables

The following environment variables can be used to override configuration settings:

| Variable | Description |
|----------|-------------|
| `SCRAPER_MODE` | Processing mode: `dev` or `prod` |
| `RAG_API_KEY` | API key for production mode |
| `SCRAPER_MAX_WORKERS` | Maximum number of concurrent workers |
| `LOG_LEVEL` | Logging level |

## Operating Modes

### Development Mode

In development mode, the scraper saves content to local folders without uploading to the RAG API. This is useful for testing and development.

#### Output Structure

```
docs/
├── agriculture/
├── water/
├── weather/
├── crops/
├── farm/
├── marketplace/
├── banking/
└── chat/
```

Each domain folder contains:
- Markdown files with extracted content
- Media catalogs with references to extracted media
- Metadata files with additional information

### Production Mode

In production mode, the scraper uploads content directly to the RAG API. This requires a valid API key.

#### API Integration

The scraper integrates with the Farmovation RAG API to upload content to the appropriate domains. The API key must be set as an environment variable:

```bash
set RAG_API_KEY=your_api_key_here  # Windows
# OR
export RAG_API_KEY=your_api_key_here  # macOS/Linux
```

## URL Management

### URL Sources

The scraper can process URLs from multiple sources:

1. **Command Line Arguments**:
   ```bash
   python -m scraper --urls https://example.com https://example.org
   ```

2. **URL File**:
   ```bash
   python -m scraper --url-file=urls.txt
   ```
   
   Supported file formats:
   - Text file (one URL per line)
   - CSV file (URLs in the first column)
   - JSON file (array of URLs or object with `urls` property)

3. **Default URLs**:
   ```bash
   python -m scraper --use-default-urls
   ```
   
   The default URLs include agricultural websites like:
   - https://pac.com.pk/
   - https://ztbl.com.pk/
   - https://ffc.com.pk/kashtkar-desk/
   - And more...

### Deep Crawling

The scraper supports deep crawling to follow links within a website:

```bash
python -m scraper --urls https://example.com --max-depth=3
```

This will crawl the initial URL and follow links up to the specified depth.

## Content Processing

### HTML to Markdown Conversion

The scraper converts HTML content to clean, structured markdown for better compatibility with LLMs and the RAG system. The conversion preserves:

- Headings and formatting
- Lists and tables
- Code blocks with language detection
- Links and references

### Content Quality Validation

The scraper validates content quality to ensure only valuable content is processed:

- Minimum content length checks
- Duplicate detection using content hashing
- Language detection and encoding handling
- Auto-generated content detection

## Media Extraction

### Media Types

The scraper extracts and catalogs various media types:

- Images with alt text and metadata
- Downloadable files (PDF, DOC, XLS, etc.)
- Audio and video files

### Media Storage

In development mode, media files are stored in organized folders:

```
files/
├── images/
├── documents/
├── audio/
├── video/
└── other/
```

Each file is stored with metadata including:
- Original URL
- Content type
- Size
- Extraction timestamp

### Media Catalogs

For each processed URL, the scraper generates a media catalog with references to all extracted media. This catalog is stored alongside the markdown content.

## Domain Classification

### RAG Domains

The scraper classifies content into the following RAG domains:

| Domain | Description | Keywords |
|--------|-------------|----------|
| agriculture | General farming knowledge | farm, crop, soil, organic, agriculture |
| water | Water management systems | irrigation, water, drainage, hydro |
| weather | Weather intelligence | weather, climate, forecast, meteorology |
| crops | Crop health monitoring | crop, plant, disease, pest, harvest |
| farm | Farm operations | equipment, machinery, operation, management |
| marketplace | Agricultural marketplace | market, price, commodity, trade |
| banking | Banking & insurance | loan, insurance, finance, credit |
| chat | Conversation memory | conversation, chat, dialogue, interaction |

### Classification Process

Content is classified based on keyword matching and relevance scoring. A single document can be assigned to multiple domains if it's relevant to multiple areas.

### Custom Domain Keywords

You can customize the domain keywords in the configuration file:

```yaml
domains:
  agriculture: ["custom", "keywords", "here"]
  # Other domains...
```

## Performance Tuning

### Concurrency Settings

Adjust the number of concurrent workers to optimize performance:

```bash
python -m scraper --max-workers=5
```

### Rate Limiting

Set the rate limit to avoid overwhelming target servers:

```bash
python -m scraper --rate-limit=2.0
```

This sets a 2-second delay between requests to the same domain.

### Memory Management

For large crawling operations, consider:

1. Limiting the crawl depth:
   ```bash
   python -m scraper --max-depth=2
   ```

2. Processing URLs in smaller batches
3. Disabling JavaScript execution for simple sites:
   ```bash
   python -m scraper --no-js
   ```

## Logging and Monitoring

### Log Levels

Set the logging level to control verbosity:

```bash
python -m scraper --log-level=DEBUG
```

Available levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Log Files

Logs are stored in the `logs` directory by default. The log file path and rotation settings can be configured:

```yaml
logging:
  level: "INFO"
  file: "./logs/scraper.log"
  max_size: "100MB"
  backup_count: 5
```

### Progress Monitoring

The scraper provides real-time progress updates during execution, including:

- URLs processed
- Success/failure counts
- Processing time
- Current operation

## Advanced Features

### JavaScript Execution

The scraper supports JavaScript execution to handle dynamic content:

```bash
# Enable JavaScript (default)
python -m scraper --urls https://example.com

# Disable JavaScript
python -m scraper --urls https://example.com --no-js
```

### Authentication Support

For sites requiring authentication, you can provide credentials through environment variables:

```bash
set SITE_USERNAME=your_username
set SITE_PASSWORD=your_password
python -m scraper --urls https://example.com
```

### Custom JavaScript Injection

You can provide custom JavaScript to execute on each page by creating a JavaScript file and referencing it in the configuration:

```yaml
crawl4ai:
  custom_js_file: "./scripts/custom_interaction.js"
```

### Batch Processing

For large sets of URLs, use batch processing to improve efficiency:

```bash
python -m scraper --url-file=large_url_list.txt --max-workers=20
```

This will process URLs in parallel with up to 20 concurrent workers.