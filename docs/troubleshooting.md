# Troubleshooting Guide

## Table of Contents

1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Configuration Errors](#configuration-errors)
4. [URL Processing Issues](#url-processing-issues)
5. [Crawling Problems](#crawling-problems)
6. [Content Processing Issues](#content-processing-issues)
7. [Media Extraction Problems](#media-extraction-problems)
8. [RAG API Integration Issues](#rag-api-integration-issues)
9. [Performance Problems](#performance-problems)
10. [Log Analysis](#log-analysis)
11. [Debugging Techniques](#debugging-techniques)

## Common Issues

### Issue: Scraper fails to start

**Symptoms:**
- Error message when running the scraper
- Process exits immediately

**Possible Causes:**
1. Missing dependencies
2. Invalid configuration
3. Python version incompatibility

**Solutions:**
1. Verify all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Check configuration file exists and is valid:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
   ```

3. Verify Python version (3.8+ required):
   ```bash
   python --version
   ```

### Issue: No output generated

**Symptoms:**
- Scraper runs without errors but no files are created
- No content in output directories

**Possible Causes:**
1. No valid URLs to process
2. URLs are inaccessible
3. Output directory permissions

**Solutions:**
1. Check URL validity:
   ```bash
   python -m scraper --urls https://example.com --log-level=DEBUG
   ```

2. Verify output directory permissions:
   ```bash
   # Windows
   icacls docs
   
   # Linux/macOS
   ls -la docs
   ```

3. Try with default URLs:
   ```bash
   python -m scraper --use-default-urls --log-level=DEBUG
   ```

## Installation Problems

### Issue: Dependency installation fails

**Symptoms:**
- Errors during `pip install -r requirements.txt`
- Missing modules when running the scraper

**Possible Causes:**
1. Incompatible Python version
2. Missing system dependencies
3. Network issues

**Solutions:**
1. Verify Python version:
   ```bash
   python --version
   ```

2. Install system dependencies:
   ```bash
   # Windows (requires administrator privileges)
   pip install wheel setuptools
   
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install python3-dev build-essential
   ```

3. Try installing dependencies one by one:
   ```bash
   pip install aiohttp
   pip install crawl4ai
   # Continue with other dependencies
   ```

### Issue: crawl4ai installation problems

**Symptoms:**
- Errors specifically related to crawl4ai
- Browser automation issues

**Possible Causes:**
1. Missing browser dependencies
2. Incompatible browser versions
3. Permission issues

**Solutions:**
1. Install browser dependencies:
   ```bash
   # Install playwright browsers
   python -m playwright install
   ```

2. Verify browser installation:
   ```bash
   python -c "from playwright.sync_api import sync_playwright; with sync_playwright() as p: browser = p.chromium.launch(); browser.close()"
   ```

3. Check for browser compatibility issues:
   ```bash
   python -m crawl4ai.diagnostics
   ```

## Configuration Errors

### Issue: Configuration validation fails

**Symptoms:**
- Error message: "Configuration validation failed"
- Scraper exits with error code 1

**Possible Causes:**
1. Invalid YAML/JSON syntax
2. Missing required fields
3. Invalid values

**Solutions:**
1. Validate configuration file syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
   ```

2. Check for required fields:
   ```bash
   python -c "import yaml; config = yaml.safe_load(open('config/config.yaml')); print('scraper' in config, 'storage' in config)"
   ```

3. Create a new default configuration:
   ```bash
   # Rename existing config
   ren config/config.yaml config/config.yaml.bak
   
   # Run scraper to generate default config
   python -m scraper --examples
   ```

### Issue: Environment variables not recognized

**Symptoms:**
- Configuration not overridden by environment variables
- API key not found in production mode

**Possible Causes:**
1. Environment variables not set correctly
2. Variable name mismatch
3. Scope issues

**Solutions:**
1. Verify environment variables are set:
   ```bash
   # Windows
   echo %RAG_API_KEY%
   
   # Linux/macOS
   echo $RAG_API_KEY
   ```

2. Set variables directly before running:
   ```bash
   # Windows
   set RAG_API_KEY=your_key_here && python -m scraper --mode=prod
   
   # Linux/macOS
   RAG_API_KEY=your_key_here python -m scraper --mode=prod
   ```

3. Check for variable name case sensitivity:
   ```bash
   # Windows
   set | findstr API_KEY
   
   # Linux/macOS
   env | grep API_KEY
   ```

## URL Processing Issues

### Issue: URLs not recognized

**Symptoms:**
- "No URLs to process" error
- URLs provided but not processed

**Possible Causes:**
1. Invalid URL format
2. URL file not found or invalid
3. Command line argument parsing issues

**Solutions:**
1. Check URL format:
   ```bash
   python -m scraper --urls http://example.com --log-level=DEBUG
   ```
   Note: URLs must include protocol (http:// or https://)

2. Verify URL file exists and is readable:
   ```bash
   type urls.txt  # Windows
   # OR
   cat urls.txt   # Linux/macOS
   ```

3. Try different URL input methods:
   ```bash
   # Direct URL
   python -m scraper --urls http://example.com
   
   # URL file
   python -m scraper --url-file=urls.txt
   
   # Default URLs
   python -m scraper --use-default-urls
   ```

### Issue: URL validation fails

**Symptoms:**
- "Invalid URL" errors
- URLs skipped during processing

**Possible Causes:**
1. Malformed URLs
2. URLs without protocol
3. Non-HTTP/HTTPS URLs

**Solutions:**
1. Check URL format:
   ```bash
   # Ensure URLs have protocol
   python -m scraper --urls https://example.com
   ```

2. Validate URLs before processing:
   ```python
   # Create a validation script
   with open('validate_urls.py', 'w') as f:
       f.write('''
import sys
from urllib.parse import urlparse

urls = sys.argv[1:]
for url in urls:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        print(f"Valid: {url}")
    else:
        print(f"Invalid: {url}")
''')

   # Run validation
   python validate_urls.py https://example.com example.com
   ```

3. Fix URL file format:
   ```bash
   # Add protocol to URLs without it
   python -c "with open('urls.txt', 'r') as f, open('fixed_urls.txt', 'w') as out: [out.write(('https://' + line.strip() if not line.strip().startswith('http') else line.strip()) + '\n') for line in f]"
   ```

## Crawling Problems

### Issue: JavaScript execution fails

**Symptoms:**
- Dynamic content not captured
- Incomplete page content
- JavaScript errors in logs

**Possible Causes:**
1. Browser configuration issues
2. JavaScript errors on target site
3. Browser compatibility problems

**Solutions:**
1. Disable JavaScript execution to test:
   ```bash
   python -m scraper --urls https://example.com --no-js
   ```

2. Increase page timeout:
   ```bash
   python -m scraper --urls https://example.com --timeout=60
   ```

3. Check browser compatibility:
   ```bash
   python -m crawl4ai.diagnostics
   ```

### Issue: Rate limiting or blocking

**Symptoms:**
- "Access denied" errors
- 403 Forbidden responses
- Inconsistent crawling results

**Possible Causes:**
1. Target site has anti-bot measures
2. Too many requests in short time
3. IP address blocked

**Solutions:**
1. Increase rate limiting:
   ```bash
   python -m scraper --urls https://example.com --rate-limit=5.0
   ```

2. Reduce concurrent workers:
   ```bash
   python -m scraper --urls https://example.com --max-workers=1
   ```

3. Add delay between requests:
   ```bash
   # Modify config.yaml
   # Set scroll_delay to higher value (e.g., 2.0)
   ```

### Issue: Deep crawling not working

**Symptoms:**
- Only initial page crawled
- No links followed
- Missing content from linked pages

**Possible Causes:**
1. Max depth set to 0 or 1
2. Links not detected correctly
3. Same-domain filtering issues

**Solutions:**
1. Increase max depth:
   ```bash
   python -m scraper --urls https://example.com --max-depth=3
   ```

2. Check link extraction in debug logs:
   ```bash
   python -m scraper --urls https://example.com --log-level=DEBUG
   ```

3. Verify domain parsing:
   ```python
   # Create a domain check script
   with open('check_domain.py', 'w') as f:
       f.write('''
from urllib.parse import urlparse
url = input("Enter URL: ")
print(f"Domain: {urlparse(url).netloc}")
''')

   # Run domain check
   python check_domain.py
   ```

## Content Processing Issues

### Issue: HTML to Markdown conversion problems

**Symptoms:**
- Malformed markdown output
- Missing content sections
- Formatting issues

**Possible Causes:**
1. Complex HTML structure
2. Unsupported HTML elements
3. Encoding issues

**Solutions:**
1. Check raw HTML content:
   ```bash
   # Enable debug logging
   python -m scraper --urls https://example.com --log-level=DEBUG
   
   # Check logs for HTML content
   ```

2. Test with simpler pages:
   ```bash
   python -m scraper --urls https://example.com/simple-page
   ```

3. Modify conversion settings in code:
   ```python
   # Create a test conversion script
   with open('test_conversion.py', 'w') as f:
       f.write('''
import sys
from html2text import HTML2Text

html = sys.stdin.read()
converter = HTML2Text()
converter.ignore_links = False
converter.ignore_images = False
converter.ignore_tables = False
print(converter.handle(html))
''')

   # Test conversion
   type sample.html | python test_conversion.py
   ```

### Issue: Content quality filtering

**Symptoms:**
- Content skipped due to quality filters
- "Content below quality threshold" messages
- Empty output files

**Possible Causes:**
1. Content too short
2. Low-quality content detection
3. Duplicate content

**Solutions:**
1. Disable quality filtering (modify code):
   ```python
   # Modify content_processor.py
   # Set min_content_length to lower value
   ```

2. Check content hashing:
   ```bash
   # Enable debug logging
   python -m scraper --urls https://example.com --log-level=DEBUG
   
   # Check logs for content hash values
   ```

3. Test with known high-quality content:
   ```bash
   python -m scraper --urls https://en.wikipedia.org/wiki/Agriculture
   ```

## Media Extraction Problems

### Issue: Images not downloaded

**Symptoms:**
- No images in files directory
- Missing image references in media catalog
- Download errors in logs

**Possible Causes:**
1. Image URLs not detected
2. Download permissions
3. Network issues

**Solutions:**
1. Check image extraction:
   ```bash
   # Enable debug logging
   python -m scraper --urls https://example.com --log-level=DEBUG
   
   # Check logs for image URLs
   ```

2. Verify file permissions:
   ```bash
   # Windows
   icacls files
   
   # Linux/macOS
   ls -la files
   ```

3. Test with image-rich site:
   ```bash
   python -m scraper --urls https://unsplash.com
   ```

### Issue: File downloads failing

**Symptoms:**
- "Download failed" errors
- Incomplete files
- Missing files

**Possible Causes:**
1. File size limits
2. Server restrictions
3. Network timeouts

**Solutions:**
1. Increase timeout:
   ```bash
   python -m scraper --urls https://example.com --timeout=120
   ```

2. Check download directory:
   ```bash
   # Windows
   dir files /s
   
   # Linux/macOS
   find files -type f | wc -l
   ```

3. Test with direct file URL:
   ```bash
   python -m scraper --urls https://example.com/sample.pdf
   ```

## RAG API Integration Issues

### Issue: Authentication failures

**Symptoms:**
- "API key not found" errors
- 401 Unauthorized responses
- Authentication failures

**Possible Causes:**
1. Missing API key
2. Invalid API key format
3. Expired or revoked API key

**Solutions:**
1. Verify API key is set:
   ```bash
   # Windows
   echo %RAG_API_KEY%
   
   # Linux/macOS
   echo $RAG_API_KEY
   ```

2. Check API key format:
   ```bash
   # Should start with "ragnar_"
   # Windows
   echo %RAG_API_KEY% | findstr /r "^ragnar_"
   
   # Linux/macOS
   echo $RAG_API_KEY | grep -E "^ragnar_"
   ```

3. Test API key directly:
   ```bash
   # Windows
   curl -H "Authorization: Bearer %RAG_API_KEY%" http://217.154.66.145:8000/auth/me
   
   # Linux/macOS
   curl -H "Authorization: Bearer $RAG_API_KEY" http://217.154.66.145:8000/auth/me
   ```

### Issue: Document upload failures

**Symptoms:**
- "Upload failed" errors
- API error responses
- Fallback to local storage

**Possible Causes:**
1. Network connectivity issues
2. Invalid document format
3. API rate limiting

**Solutions:**
1. Check API connectivity:
   ```bash
   # Windows
   ping 217.154.66.145
   
   # Linux/macOS
   ping -c 4 217.154.66.145
   ```

2. Test with minimal document:
   ```bash
   # Windows
   curl -X POST "http://217.154.66.145:8000/api/v1/documents/agriculture" ^
     -H "Authorization: Bearer %RAG_API_KEY%" ^
     -H "Content-Type: application/json" ^
     -d "{\"text\": \"Test document\", \"metadata\": {\"source\": \"test\"}}"
   
   # Linux/macOS
   curl -X POST "http://217.154.66.145:8000/api/v1/documents/agriculture" \
     -H "Authorization: Bearer $RAG_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"text": "Test document", "metadata": {"source": "test"}}'
   ```

3. Check for rate limiting:
   ```bash
   # Enable debug logging
   python -m scraper --mode=prod --urls https://example.com --log-level=DEBUG
   
   # Look for 429 responses in logs
   ```

### Issue: Domain classification problems

**Symptoms:**
- Content assigned to wrong domains
- All content defaulting to agriculture domain
- Classification errors in logs

**Possible Causes:**
1. Insufficient content for classification
2. Keyword configuration issues
3. Content language not matching keywords

**Solutions:**
1. Check domain keywords:
   ```bash
   # View domain configuration
   python -c "import yaml; config = yaml.safe_load(open('config/config.yaml')); print(config.get('domains', {}))"
   ```

2. Test with domain-specific content:
   ```bash
   python -m scraper --mode=prod --urls https://weather.com
   ```

3. Add more specific keywords:
   ```yaml
   # Modify config.yaml
   domains:
     weather:
       - weather
       - forecast
       - temperature
       - precipitation
       - humidity
       - meteorology
       - climate
       # Add more specific keywords
   ```

## Performance Problems

### Issue: Slow processing

**Symptoms:**
- Long processing times
- High CPU/memory usage
- Timeouts

**Possible Causes:**
1. Too many concurrent workers
2. JavaScript execution overhead
3. Large pages or deep crawling

**Solutions:**
1. Adjust worker count:
   ```bash
   # Reduce workers for less resource usage
   python -m scraper --urls https://example.com --max-workers=5
   
   # Increase workers for faster processing (if resources allow)
   python -m scraper --urls https://example.com --max-workers=20
   ```

2. Disable JavaScript for simple sites:
   ```bash
   python -m scraper --urls https://example.com --no-js
   ```

3. Limit crawl depth:
   ```bash
   python -m scraper --urls https://example.com --max-depth=1
   ```

### Issue: Memory usage problems

**Symptoms:**
- Out of memory errors
- System slowdown
- Process killed by OS

**Possible Causes:**
1. Too many concurrent workers
2. Large pages or files
3. Memory leaks

**Solutions:**
1. Reduce concurrent workers:
   ```bash
   python -m scraper --urls https://example.com --max-workers=3
   ```

2. Process URLs in smaller batches:
   ```bash
   # Create smaller URL files
   python -c "with open('urls.txt', 'r') as f, open('batch1.txt', 'w') as out: [out.write(line) for i, line in enumerate(f) if i < 10]"
   
   # Process each batch separately
   python -m scraper --url-file=batch1.txt
   ```

3. Monitor memory usage:
   ```bash
   # Windows
   start "Memory Monitor" powershell -Command "while($true) { Get-Process -Name python | Select-Object WorkingSet; Start-Sleep -Seconds 5 }"
   
   # Linux/macOS
   watch -n 5 "ps -o pid,user,%mem,command ax | grep python"
   ```

## Log Analysis

### Reading Log Files

The default log file is located at `./logs/scraper.log`. To analyze logs:

```bash
# Windows
type logs\scraper.log | findstr ERROR
type logs\scraper.log | findstr WARNING

# Linux/macOS
grep ERROR logs/scraper.log
grep WARNING logs/scraper.log
```

### Common Log Patterns

1. **URL Processing**:
   ```
   INFO - Processing URL: https://example.com
   ```

2. **Crawling Results**:
   ```
   INFO - Successfully crawled: https://example.com
   ```

3. **Content Processing**:
   ```
   INFO - Converted HTML to markdown (12345 bytes)
   ```

4. **Domain Classification**:
   ```
   INFO - Classified content to domains: ['agriculture', 'crops']
   ```

5. **Storage/Upload**:
   ```
   INFO - Saved document to agriculture domain with ID: doc_123
   INFO - Uploaded document to agriculture domain with ID: uuid-123
   ```

6. **Errors**:
   ```
   ERROR - Failed to crawl https://example.com: Connection refused
   ERROR - Failed to upload to RAG API: 401 Unauthorized
   ```

### Creating Log Analysis Scripts

Create a simple log analysis script:

```python
# Create log_analysis.py
with open('log_analysis.py', 'w') as f:
    f.write('''
import sys
import re
from collections import Counter

log_file = sys.argv[1] if len(sys.argv) > 1 else "logs/scraper.log"

# Patterns to extract
url_pattern = re.compile(r"Processing URL: (https?://[^\s]+)")
error_pattern = re.compile(r"ERROR - (.+)")
domain_pattern = re.compile(r"Classified content to domains: \[(.*?)\]")

urls = []
errors = []
domains = []

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        url_match = url_pattern.search(line)
        if url_match:
            urls.append(url_match.group(1))
            
        error_match = error_pattern.search(line)
        if error_match:
            errors.append(error_match.group(1))
            
        domain_match = domain_pattern.search(line)
        if domain_match:
            domains_str = domain_match.group(1)
            domains.extend([d.strip().strip("'") for d in domains_str.split(',')])

print(f"URLs processed: {len(urls)}")
print(f"Errors encountered: {len(errors)}")
print(f"Top 5 domains:")
for domain, count in Counter(domains).most_common(5):
    print(f"  {domain}: {count}")

if errors:
    print("\\nTop 5 errors:")
    for error, count in Counter(errors).most_common(5):
        print(f"  {error}: {count}")
''')

# Run analysis
python log_analysis.py
```

## Debugging Techniques

### Enabling Debug Logging

```bash
python -m scraper --urls https://example.com --log-level=DEBUG
```

### Tracing URL Processing

```bash
# Create a URL trace script
with open('trace_url.py', 'w') as f:
    f.write('''
import sys
import re

log_file = sys.argv[1] if len(sys.argv) > 1 else "logs/scraper.log"
target_url = sys.argv[2] if len(sys.argv) > 2 else None

if not target_url:
    print("Usage: python trace_url.py [log_file] [url]")
    sys.exit(1)

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        if target_url in line:
            print(line.strip())
''')

# Run trace
python trace_url.py logs/scraper.log https://example.com
```

### Testing Individual Components

1. **URL Manager**:
   ```python
   # Create test script
   with open('test_url_manager.py', 'w') as f:
       f.write('''
import yaml
import sys
sys.path.append('.')
from scraper.core.config import ConfigManager
from scraper.utils.component_factory import create_url_manager

# Load config
config_manager = ConfigManager()
config = config_manager.load_config()

# Create URL manager
url_manager = create_url_manager(config)

# Test URL validation
urls = [
    "https://example.com",
    "example.com",  # Missing protocol
    "https://invalid url.com",  # Invalid URL
    "ftp://example.com"  # Non-HTTP protocol
]

print("URL Validation Results:")
valid_urls = url_manager.validate_urls(urls)
for url in urls:
    print(f"{url}: {'Valid' if url in valid_urls else 'Invalid'}")
''')

   # Run test
   python test_url_manager.py
   ```

2. **Content Processor**:
   ```python
   # Create test script
   with open('test_content_processor.py', 'w') as f:
       f.write('''
import yaml
import sys
sys.path.append('.')
from scraper.core.config import ConfigManager
from scraper.utils.component_factory import create_content_processor
from scraper.core.base import CrawlResult

# Load config
config_manager = ConfigManager()
config = config_manager.load_config()

# Create content processor
content_processor = create_content_processor(config)

# Test HTML to markdown conversion
html = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Test Heading</h1>
    <p>This is a test paragraph.</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
</body>
</html>
"""

# Create mock crawl result
crawl_result = CrawlResult(
    url="https://example.com",
    html=html,
    markdown="",
    links=[],
    media=[],
    metadata={"title": "Test Page"},
    success=True,
    error_message=""
)

# Process content
markdown = content_processor.convert_to_markdown(html)
print("Converted Markdown:")
print(markdown)

# Create document
document = content_processor.create_document(
    crawl_result,
    ["agriculture"],
    {}
)
print("\\nDocument:")
print(f"Title: {document.title}")
print(f"URL: {document.url}")
print(f"Content Hash: {document.content_hash}")
print(f"Domain Classifications: {document.domain_classifications}")
''')

   # Run test
   python test_content_processor.py
   ```

3. **RAG Uploader**:
   ```python
   # Create test script
   with open('test_rag_uploader.py', 'w') as f:
       f.write('''
import yaml
import asyncio
import sys
sys.path.append('.')
from scraper.core.config import ConfigManager
from scraper.utils.component_factory import create_rag_uploader
from scraper.core.base import ScrapedDocument
from datetime import datetime

# Load config
config_manager = ConfigManager()
config = config_manager.load_config()

# Create RAG uploader
rag_uploader = create_rag_uploader(config)

# Test document
document = ScrapedDocument(
    url="https://example.com",
    title="Test Document",
    content="<p>Test content</p>",
    markdown="# Test Document\\n\\nTest content",
    metadata={"source": "test"},
    media_catalog=[],
    domain_classifications=["agriculture"],
    timestamp=datetime.now(),
    content_hash="test_hash",
    processing_time=1.0,
    retry_count=0
)

async def test_uploader():
    # Initialize uploader
    await rag_uploader.initialize()
    
    # Test API connectivity
    print("Testing API connectivity...")
    try:
        result = await rag_uploader._test_api_connectivity()
        print(f"API connectivity test: {'Success' if result else 'Failed'}")
    except Exception as e:
        print(f"API connectivity error: {e}")
    
    # Test document upload
    print("\\nTesting document upload...")
    try:
        doc_id = await rag_uploader.upload_document(document, "agriculture")
        print(f"Document uploaded with ID: {doc_id}")
    except Exception as e:
        print(f"Upload error: {e}")
    
    # Clean up
    await rag_uploader.cleanup()

# Run test
asyncio.run(test_uploader())
''')

   # Run test
   python test_rag_uploader.py
   ```