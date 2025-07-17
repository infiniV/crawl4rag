# Example Configurations

This document provides example configurations for different use cases of the Production Web Scraper. Each configuration is optimized for specific scenarios and can be used as a starting point for your own configuration.

## Table of Contents

1. [Basic Configuration](#basic-configuration)
2. [High-Performance Configuration](#high-performance-configuration)
3. [Deep Crawling Configuration](#deep-crawling-configuration)
4. [Media-Focused Configuration](#media-focused-configuration)
5. [Low-Resource Configuration](#low-resource-configuration)
6. [Custom Domain Configuration](#custom-domain-configuration)
7. [Production RAG API Configuration](#production-rag-api-configuration)
8. [Advanced JavaScript Configuration](#advanced-javascript-configuration)
9. [Using Configuration Files](#using-configuration-files)

## Basic Configuration

This is the default configuration that works well for most use cases.

```yaml
scraper:
  mode: "dev"
  max_workers: 10
  max_depth: 3
  rate_limit: 1.0
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

## High-Performance Configuration

This configuration is optimized for high-performance crawling of many URLs.

```yaml
scraper:
  mode: "dev"
  max_workers: 30  # Increased worker count
  max_depth: 2     # Reduced depth to focus on breadth
  rate_limit: 0.5  # Reduced rate limit for faster crawling
  timeout: 20      # Reduced timeout for faster processing
  
crawl4ai:
  headless: true
  wait_for_images: false  # Don't wait for images to load
  scan_full_page: true
  scroll_delay: 0.2       # Reduced scroll delay
  accept_downloads: true
  
storage:
  dev:
    base_path: "./docs"
    files_path: "./files"
  prod:
    rag_api_url: "http://217.154.66.145:8000"
    api_key_env: "RAG_API_KEY"
    
# Domain configuration same as basic
    
logging:
  level: "WARNING"  # Reduced logging for better performance
  file: "./logs/scraper.log"
  max_size: "100MB"
  backup_count: 5
```

## Deep Crawling Configuration

This configuration is optimized for deep crawling of websites to extract comprehensive content.

```yaml
scraper:
  mode: "dev"
  max_workers: 15
  max_depth: 10     # Increased depth for deep crawling
  rate_limit: 2.0   # Increased rate limit to be more respectful
  timeout: 60       # Increased timeout for complex pages
  
crawl4ai:
  headless: true
  wait_for_images: true
  scan_full_page: true
  scroll_delay: 1.0  # Increased scroll delay for better content loading
  accept_downloads: true
  
storage:
  dev:
    base_path: "./docs_deep"  # Separate output directory
    files_path: "./files_deep"
  prod:
    rag_api_url: "http://217.154.66.145:8000"
    api_key_env: "RAG_API_KEY"
    
# Domain configuration same as basic
    
logging:
  level: "INFO"
  file: "./logs/deep_scraper.log"  # Separate log file
  max_size: "200MB"                # Increased log size
  backup_count: 10
```

## Media-Focused Configuration

This configuration is optimized for extracting media files (images, documents, etc.) from websites.

```yaml
scraper:
  mode: "dev"
  max_workers: 8     # Reduced workers to handle larger files
  max_depth: 3
  rate_limit: 1.5    # Increased rate limit for media downloads
  timeout: 120       # Increased timeout for large file downloads
  
crawl4ai:
  headless: true
  wait_for_images: true  # Wait for images to load
  scan_full_page: true
  scroll_delay: 1.0      # Increased scroll delay for media loading
  accept_downloads: true
  
storage:
  dev:
    base_path: "./docs"
    files_path: "./media_files"  # Dedicated media directory
  prod:
    rag_api_url: "http://217.154.66.145:8000"
    api_key_env: "RAG_API_KEY"
    
# Domain configuration same as basic

# Additional media configuration
media:
  max_file_size: 100000000  # 100MB max file size
  download_timeout: 300     # 5 minutes download timeout
  retry_count: 3            # Retry downloads 3 times
  file_types:               # Prioritized file types
    - pdf
    - docx
    - xlsx
    - pptx
    - jpg
    - png
    
logging:
  level: "INFO"
  file: "./logs/media_scraper.log"
  max_size: "200MB"
  backup_count: 5
```

## Low-Resource Configuration

This configuration is optimized for running on systems with limited resources.

```yaml
scraper:
  mode: "dev"
  max_workers: 3      # Reduced worker count
  max_depth: 1        # No deep crawling
  rate_limit: 2.0     # Slower rate to reduce resource usage
  timeout: 30
  
crawl4ai:
  headless: true
  wait_for_images: false  # Don't wait for images
  scan_full_page: false   # Don't scan full page
  scroll_delay: 0.0       # No scrolling
  accept_downloads: false # Don't download files
  
storage:
  dev:
    base_path: "./docs_lite"
    files_path: "./files_lite"
  prod:
    rag_api_url: "http://217.154.66.145:8000"
    api_key_env: "RAG_API_KEY"
    
# Domain configuration same as basic
    
logging:
  level: "WARNING"  # Minimal logging
  file: "./logs/scraper_lite.log"
  max_size: "10MB"
  backup_count: 2
```

## Custom Domain Configuration

This configuration demonstrates how to customize domain classification for specific industries.

```yaml
scraper:
  mode: "dev"
  max_workers: 10
  max_depth: 3
  rate_limit: 1.0
  timeout: 30
  
# Other standard configuration sections...
    
domains:
  # Standard domains with expanded keywords
  agriculture: [
    "farm", "crop", "soil", "organic", "agriculture", "farming", 
    "cultivation", "planting", "harvesting", "fertilizer", "pesticide"
  ]
  water: [
    "irrigation", "water", "drainage", "hydro", "aquifer", "groundwater",
    "reservoir", "dam", "canal", "sprinkler", "drip", "moisture"
  ]
  weather: [
    "weather", "climate", "forecast", "meteorology", "precipitation",
    "temperature", "humidity", "barometric", "pressure", "wind", "storm"
  ]
  
  # Custom domains for specific industries
  dairy: [
    "milk", "dairy", "cow", "cattle", "cheese", "yogurt", "butter",
    "cream", "pasteurization", "homogenization", "lactose"
  ]
  poultry: [
    "chicken", "poultry", "egg", "broiler", "layer", "hatchery",
    "incubation", "feed", "coop", "avian", "fowl"
  ]
  sustainable: [
    "sustainable", "organic", "regenerative", "conservation", "biodiversity",
    "ecosystem", "renewable", "carbon", "sequestration", "permaculture"
  ]
```

## Production RAG API Configuration

This configuration is optimized for production use with the RAG API.

```yaml
scraper:
  mode: "prod"  # Production mode
  max_workers: 15
  max_depth: 3
  rate_limit: 1.0
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
    batch_size: 10           # Upload documents in batches of 10
    retry_count: 5           # Retry uploads 5 times
    retry_delay: 1.0         # Initial retry delay
    max_retry_delay: 60.0    # Maximum retry delay
    
# Domain configuration same as basic
    
logging:
  level: "INFO"
  file: "./logs/prod_scraper.log"
  max_size: "200MB"
  backup_count: 10
```

## Advanced JavaScript Configuration

This configuration demonstrates advanced JavaScript handling for complex websites.

```yaml
scraper:
  mode: "dev"
  max_workers: 8
  max_depth: 3
  rate_limit: 1.5
  timeout: 60  # Increased timeout for JS execution
  
crawl4ai:
  headless: true
  wait_for_images: true
  scan_full_page: true
  scroll_delay: 1.0
  accept_downloads: true
  js_code: |
    // Wait for page to fully load
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Scroll through the page to trigger lazy loading
    for (let i = 0; i < 5; i++) {
      window.scrollBy(0, window.innerHeight);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    // Click on "Show More" buttons
    const showMoreButtons = Array.from(document.querySelectorAll('button, a')).filter(
      el => el.textContent.match(/show more|load more|view more/i)
    );
    for (const button of showMoreButtons) {
      try {
        button.click();
        await new Promise(resolve => setTimeout(resolve, 2000));
      } catch (e) {
        console.error('Error clicking button:', e);
      }
    }
    
    // Expand collapsed content
    const expandButtons = Array.from(document.querySelectorAll('button, a, .expand, .collapse')).filter(
      el => el.textContent.match(/expand|show|more|\+/i) || el.classList.contains('expand')
    );
    for (const button of expandButtons) {
      try {
        button.click();
        await new Promise(resolve => setTimeout(resolve, 1000));
      } catch (e) {
        console.error('Error expanding content:', e);
      }
    }
    
    // Wait for any final content to load
    await new Promise(resolve => setTimeout(resolve, 2000));
  
# Other standard configuration sections...
```

## Using Configuration Files

### Saving a Configuration

To save a configuration to a file:

1. Create a YAML file with your configuration:
   ```bash
   # Windows
   copy config\config.yaml config\high_performance.yaml
   
   # Linux/macOS
   cp config/config.yaml config/high_performance.yaml
   ```

2. Edit the file with your preferred configuration settings.

### Using a Custom Configuration

To use a custom configuration file:

```bash
python -m scraper --config=config/high_performance.yaml --urls https://example.com
```

### Overriding Configuration Settings

You can override specific configuration settings via command line arguments:

```bash
python -m scraper --config=config/high_performance.yaml --max-workers=5 --max-depth=2 --urls https://example.com
```

This will use the high_performance.yaml configuration but override the max_workers and max_depth settings.

### Environment Variables

You can also use environment variables to override configuration settings:

```bash
# Windows
set SCRAPER_MAX_WORKERS=5
set LOG_LEVEL=DEBUG
python -m scraper --config=config/high_performance.yaml --urls https://example.com

# Linux/macOS
SCRAPER_MAX_WORKERS=5 LOG_LEVEL=DEBUG python -m scraper --config=config/high_performance.yaml --urls https://example.com
```