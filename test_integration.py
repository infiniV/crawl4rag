"""
Integration test for Production Web Scraper

Tests the integration between URL Manager and Crawl Engine components.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from scraper.core import (
    URLManager, 
    CrawlEngine, 
    ConfigManager,
    CrawlResult
)


@pytest.mark.asyncio
async def test_url_manager_with_crawl_engine():
    """Test integration between URL Manager and Crawl Engine"""
    # Create configuration
    config = {
        'crawl': {
            'headless': True,
            'wait_for_images': False,  # Faster for testing
            'scan_full_page': False,
            'scroll_delay': 0.1,
            'accept_downloads': False,
            'timeout': 10
        },
        'max_workers': 2,
        'rate_limit': 0.1,
        'domains': {
            'allowed': ['example.com', 'test.com'],
            'excluded': ['ads.example.com']
        }
    }
    
    # Create components
    url_manager = URLManager(config)
    
    # Initialize URL Manager
    # Note: In a real implementation, we would await this coroutine
    # but for testing purposes, we'll just set the initialized flag
    url_manager._initialized = True
    
    # Add some test URLs
    test_urls = [
        'https://example.com/page1',
        'https://example.com/page2',
        'https://test.com/home',
        'https://ads.example.com/banner'  # Should be excluded
    ]
    
    # Add URLs to manager
    valid_urls = url_manager.validate_urls(test_urls)
    url_manager.add_discovered_urls(valid_urls, 0)
    
    # Create crawl engine with mocked crawler
    with patch('scraper.core.crawl_engine.AsyncWebCrawler') as mock_crawler_class:
        # Create mock results
        mock_results = []
        for url in valid_urls:
            mock_result = AsyncMock()
            mock_result.html = f"<html><body>Content for {url}</body></html>"
            mock_result.markdown = f"# Content for {url}"
            mock_result.links = [{"href": f"{url}/subpage"}]
            mock_result.media = []
            mock_result.title = f"Page {url}"
            mock_result.success = True
            mock_result.error_message = None
            mock_results.append(mock_result)
        
        # Set up mock crawler
        mock_crawler = AsyncMock()
        mock_crawler.arun.side_effect = mock_results
        mock_crawler_class.return_value = mock_crawler
        
        # Create and initialize crawl engine
        crawl_engine = CrawlEngine(config)
        await crawl_engine.initialize()
        
        # Get batch of URLs to process
        batch_size = 2
        urls_to_process = url_manager.get_next_batch(batch_size)
        
        # Process URLs with crawl engine
        results = await crawl_engine.crawl_batch(urls_to_process, {})
        
        # Verify results
        assert len(results) == batch_size
        assert all(isinstance(r, CrawlResult) for r in results)
        assert all(r.success for r in results)
        
        # Mark URLs as processed in URL manager
        for url in urls_to_process:
            url_manager.mark_processed(url, True)
        
        # Verify queue status
        queue_status = url_manager.get_queue_status()
        assert queue_status['completed'] == batch_size
        assert queue_status['pending'] == len(valid_urls) - batch_size
        
        # Clean up
        await crawl_engine.cleanup()


if __name__ == "__main__":
    asyncio.run(test_url_manager_with_crawl_engine())