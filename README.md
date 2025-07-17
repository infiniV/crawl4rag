# Production Web Scraper

A comprehensive, scalable web scraper built on crawl4ai that performs deep website scanning and integrates with the Farmovation RAG API. The system is designed with a modular architecture supporting both production and development modes, concurrent processing, intelligent content categorization, and robust error handling.

## Features

- Deep website scanning with crawl4ai
- HTML to markdown conversion
- Media extraction and downloading
- Content classification for RAG domains
- Development and production modes
- Comprehensive logging and error handling
- Configurable via YAML/JSON and environment variables

## Project Structure

```
project/
├── scraper/
│   ├── core/           # Core components and interfaces
│   ├── cli/            # Command line interface
│   ├── processors/     # Content processing components
│   ├── storage/        # Storage management components
│   └── utils/          # Utility functions
├── docs/               # Development mode output
│   ├── agriculture/
│   ├── water/
│   ├── weather/
│   ├── crops/
│   ├── farm/
│   ├── marketplace/
│   ├── banking/
│   └── chat/
├── files/              # Downloaded files
├── logs/               # Application logs
├── config/             # Configuration files
└── tests/              # Test suite
```

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Development Mode

```
python -m scraper --mode=dev --urls https://example.com
```

### Production Mode

```
export RAG_API_KEY=your_api_key
python -m scraper --mode=prod --urls https://example.com
```

### Using URL File

```
python -m scraper --url-file urls.txt
```

## Configuration

The scraper can be configured using a YAML or JSON configuration file:

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

## Environment Variables

- `SCRAPER_MODE`: Set to "dev" or "prod" to override configuration
- `RAG_API_KEY`: API key for production mode
- `SCRAPER_MAX_WORKERS`: Maximum number of concurrent workers
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## License

MIT