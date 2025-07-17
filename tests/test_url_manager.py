"""
Unit tests for URL Manager

Tests URL validation, normalization, queue management, rate limiting,
and discovered URL handling functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from scraper.core.url_manager import URLManager, URLPriority, URLStatus, URLInfo, DomainRateLimit


class TestURLManager:
    """Test cases for URL Manager"""
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
            'max_depth': 3,
            'rate_limit': 1.0,
            'max_retries': 3,
            'timeout': 30,
            'follow_external_links': False,
            'respect_robots_txt': True
        }
    
    @pytest.fixture
    def url_manager(self, config):
        """URL Manager instance for testing"""
        return URLManager(config)
    
    def test_url_normalization(self, url_manager):
        """Test URL normalization functionality"""
        test_cases = [
            ("http://example.com", "http://example.com/"),
            ("https://example.com/", "https://example.com/"),
            ("https://example.com/path/", "https://example.com/path"),
            ("https://EXAMPLE.COM/Path", "https://example.com/Path"),
            ("https://example.com:443/", "https://example.com/"),
            ("http://example.com:80/", "http://example.com/"),
            ("https://example.com/?b=2&a=1", "https://example.com/?a=1&b=2"),
            ("https://example.com/path#fragment", "https://example.com/path"),
            ("example.com", "https://example.com/")
        ]
        
        for input_url, expected in test_cases:
            result = url_manager._normalize_url(input_url)
            assert result == expected, f"Failed for {input_url}: got {result}, expected {expected}"
    
    def test_url_validation(self, url_manager):
        """Test URL validation"""
        valid_urls = [
            "https://example.com",
            "http://test.org/path",
            "https://subdomain.example.com/page"
        ]
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "javascript:alert('test')",
            "mailto:test@example.com",
            "https://example.com/file.pdf",
            "https://example.com/image.jpg"
        ]
        
        for url in valid_urls:
            assert url_manager._is_valid_url(url), f"Should be valid: {url}"
        
        for url in invalid_urls:
            assert not url_manager._is_valid_url(url), f"Should be invalid: {url}"
    
    def test_validate_urls_method(self, url_manager):
        """Test the validate_urls method"""
        input_urls = [
            "https://example.com",
            "invalid-url",
            "https://test.org/page",
            "https://example.com/file.pdf",
            "http://valid.com"
        ]
        
        result = url_manager.validate_urls(input_urls)
        
        # Should return only valid URLs, normalized
        expected = [
            "https://example.com/",
            "https://test.org/page",
            "http://valid.com/"
        ]
        
        assert len(result) == 3
        for url in expected:
            assert url in result
    
    def test_add_urls(self, url_manager):
        """Test adding URLs to the queue"""
        urls = [
            "https://example.com",
            "https://test.org/page",
            "https://example.com",  # Duplicate
            "invalid-url"  # Invalid
        ]
        
        added_count = url_manager.add_urls(urls)
        
        # Should add 2 unique valid URLs
        assert added_count == 2
        assert len(url_manager.url_queue) == 2
        assert len(url_manager.url_set) == 2
        assert url_manager.stats['total_urls'] == 2
    
    def test_add_discovered_urls(self, url_manager):
        """Test adding discovered URLs with depth"""
        urls = ["https://example.com/page1", "https://example.com/page2"]
        
        url_manager.add_discovered_urls(urls, depth=1)
        
        assert len(url_manager.url_queue) == 2
        assert url_manager.stats['discovered'] == 2
        
        # Check that URLs have correct depth and priority
        for url_info in url_manager.url_queue:
            assert url_info.depth == 1
            assert url_info.priority == URLPriority.LOW
    
    def test_depth_limiting(self, url_manager):
        """Test that URLs beyond max depth are not added"""
        urls = ["https://example.com/deep"]
        
        # Add URL at max depth + 1
        added_count = url_manager.add_urls(urls, depth=url_manager.max_depth + 1)
        
        assert added_count == 0
        assert len(url_manager.url_queue) == 0
    
    def test_get_next_batch_priority(self, url_manager):
        """Test that get_next_batch respects priority"""
        # Add URLs with different priorities
        url_manager.add_urls(["https://low.com"], priority=URLPriority.LOW)
        url_manager.add_urls(["https://high.com"], priority=URLPriority.HIGH)
        url_manager.add_urls(["https://medium.com"], priority=URLPriority.MEDIUM)
        
        batch = url_manager.get_next_batch(3)
        
        # High priority should come first
        assert "https://high.com/" in batch
        assert len(batch) == 3
    
    def test_rate_limiting(self, url_manager):
        """Test domain-based rate limiting"""
        # Add URLs from same domain
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]
        url_manager.add_urls(urls)
        
        # Get first batch
        batch1 = url_manager.get_next_batch(3)
        assert len(batch1) == 1  # Should only get one due to rate limiting
        
        # Simulate time passing
        domain_limit = url_manager.domain_limits["example.com"]
        domain_limit.last_request = datetime.now() - timedelta(seconds=2)
        
        # Get next batch
        batch2 = url_manager.get_next_batch(3)
        assert len(batch2) == 1  # Should get another one
    
    def test_mark_processed_success(self, url_manager):
        """Test marking URL as successfully processed"""
        url = "https://example.com"
        url_manager.add_urls([url])
        
        normalized_url = "https://example.com/"
        url_manager.mark_processed(normalized_url, success=True, processing_time=1.5)
        
        assert url_manager.stats['processed'] == 1
        assert normalized_url in url_manager.processed_urls
        
        # Check URL info is updated
        url_info = url_manager.processed_urls[normalized_url]
        assert url_info.status == URLStatus.COMPLETED
        assert url_info.processing_time == 1.5
    
    def test_mark_processed_failure_with_retry(self, url_manager):
        """Test marking URL as failed with retry logic"""
        url = "https://example.com"
        url_manager.add_urls([url])
        
        normalized_url = "https://example.com/"
        
        # First failure - should retry
        url_manager.mark_processed(normalized_url, success=False, error_message="Network error")
        
        assert url_manager.stats['failed'] == 0  # Not failed yet, will retry
        
        # Find URL info and check retry count
        url_info = None
        for info in url_manager.url_queue:
            if info.normalized_url == normalized_url:
                url_info = info
                break
        
        assert url_info is not None
        assert url_info.retry_count == 1
        assert url_info.status == URLStatus.PENDING
    
    def test_mark_processed_final_failure(self, url_manager):
        """Test marking URL as finally failed after max retries"""
        url = "https://example.com"
        url_manager.add_urls([url])
        
        normalized_url = "https://example.com/"
        
        # Fail multiple times to exceed max retries
        for i in range(url_manager.max_retries):
            url_manager.mark_processed(normalized_url, success=False, error_message="Persistent error")
        
        assert url_manager.stats['failed'] == 1
        assert normalized_url in url_manager.failed_urls
        
        url_info = url_manager.failed_urls[normalized_url]
        assert url_info.status == URLStatus.FAILED
        assert url_info.retry_count == url_manager.max_retries
    
    def test_domain_backoff(self, url_manager):
        """Test domain backoff after consecutive failures"""
        urls = [f"https://failing.com/page{i}" for i in range(5)]
        url_manager.add_urls(urls)
        
        # Fail multiple URLs from same domain
        for i in range(3):
            normalized_url = f"https://failing.com/page{i}"
            for retry in range(url_manager.max_retries):
                url_manager.mark_processed(normalized_url, success=False, error_message="Server error")
        
        # Domain should be in backoff
        domain_limit = url_manager.domain_limits["failing.com"]
        assert domain_limit.consecutive_failures >= 3
        assert domain_limit.backoff_until is not None
        assert domain_limit.backoff_until > datetime.now()
    
    def test_get_queue_status(self, url_manager):
        """Test queue status reporting"""
        # Add some URLs
        url_manager.add_urls(["https://example.com", "https://test.org"])
        
        # Process one successfully
        url_manager.mark_processed("https://example.com/", success=True)
        
        status = url_manager.get_queue_status()
        
        assert status['total_urls'] == 2
        assert status['completed'] == 1
        assert status['pending'] >= 0
        assert status['queue_size'] == 2
        assert status['domains_tracked'] == 2
    
    def test_extract_links_from_content(self, url_manager):
        """Test link extraction from HTML content"""
        html_content = '''
        <html>
            <body>
                <a href="/relative-link">Relative</a>
                <a href="https://external.com/page">External</a>
                <a href="https://example.com/internal">Internal</a>
                <a href="#fragment">Fragment</a>
                <a href="mailto:test@example.com">Email</a>
                <area href="/area-link">
                <link href="/stylesheet.css">
            </body>
        </html>
        '''
        
        base_url = "https://example.com/page"
        links = url_manager.extract_links_from_content(html_content, base_url)
        
        # Should extract and resolve relative links
        expected_links = [
            "https://example.com/relative-link",
            "https://example.com/internal",
            "https://example.com/area-link",
            "https://example.com/stylesheet.css"
        ]
        
        # External link should be excluded when follow_external_links is False
        for expected in expected_links:
            assert expected in links
        
        # External link should not be included
        assert "https://external.com/page" not in links
        
        # Fragment and mailto should not be included
        assert not any("#fragment" in link for link in links)
        assert not any("mailto:" in link for link in links)
    
    def test_extract_links_with_external_following(self, config):
        """Test link extraction when following external links is enabled"""
        config['follow_external_links'] = True
        url_manager = URLManager(config)
        
        html_content = '''
        <html>
            <body>
                <a href="https://external.com/page">External</a>
                <a href="https://example.com/internal">Internal</a>
            </body>
        </html>
        '''
        
        base_url = "https://example.com/page"
        links = url_manager.extract_links_from_content(html_content, base_url)
        
        # Both internal and external links should be included
        assert "https://external.com/page" in links
        assert "https://example.com/internal" in links
    
    def test_get_failed_urls(self, url_manager):
        """Test getting failed URLs information"""
        url = "https://example.com"
        url_manager.add_urls([url])
        
        normalized_url = "https://example.com/"
        
        # Fail the URL completely
        for i in range(url_manager.max_retries):
            url_manager.mark_processed(normalized_url, success=False, error_message="Test error")
        
        failed_urls = url_manager.get_failed_urls()
        
        assert len(failed_urls) == 1
        failed_info = failed_urls[0]
        assert failed_info['url'] == normalized_url
        assert failed_info['domain'] == "example.com"
        assert failed_info['retry_count'] == url_manager.max_retries
        assert failed_info['error_message'] == "Test error"
    
    def test_reset_failed_urls(self, url_manager):
        """Test resetting failed URLs for retry"""
        url = "https://example.com"
        url_manager.add_urls([url])
        
        normalized_url = "https://example.com/"
        
        # Fail the URL completely
        for i in range(url_manager.max_retries):
            url_manager.mark_processed(normalized_url, success=False, error_message="Test error")
        
        assert url_manager.stats['failed'] == 1
        assert len(url_manager.failed_urls) == 1
        
        # Reset failed URLs
        reset_count = url_manager.reset_failed_urls()
        
        assert reset_count == 1
        assert url_manager.stats['failed'] == 0
        assert len(url_manager.failed_urls) == 0
        
        # URL should be back in pending status
        url_info = None
        for info in url_manager.url_queue:
            if info.normalized_url == normalized_url:
                url_info = info
                break
        
        assert url_info is not None
        assert url_info.status == URLStatus.PENDING
        assert url_info.retry_count == 0
    
    def test_clear_queue(self, url_manager):
        """Test clearing the URL queue"""
        # Add some URLs and process them
        url_manager.add_urls(["https://example.com", "https://test.org"])
        url_manager.mark_processed("https://example.com/", success=True)
        
        # Clear queue
        url_manager.clear_queue()
        
        assert len(url_manager.url_queue) == 0
        assert len(url_manager.url_set) == 0
        assert len(url_manager.processed_urls) == 0
        assert len(url_manager.failed_urls) == 0
        assert len(url_manager.domain_limits) == 0
        assert url_manager.stats['total_urls'] == 0
        assert url_manager.stats['processed'] == 0
    
    @pytest.mark.asyncio
    async def test_check_url_accessibility_success(self, url_manager):
        """Test URL accessibility checking - success case"""
        with patch('aiohttp.ClientSession.head') as mock_head:
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_head.return_value.__aenter__.return_value = mock_response
            
            await url_manager.initialize()
            
            accessible, error = await url_manager.check_url_accessibility("https://example.com")
            
            assert accessible is True
            assert error is None
    
    @pytest.mark.asyncio
    async def test_check_url_accessibility_failure(self, url_manager):
        """Test URL accessibility checking - failure case"""
        with patch('aiohttp.ClientSession.head') as mock_head:
            # Mock failed response
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.reason = "Not Found"
            mock_head.return_value.__aenter__.return_value = mock_response
            
            await url_manager.initialize()
            
            accessible, error = await url_manager.check_url_accessibility("https://example.com/notfound")
            
            assert accessible is False
            assert "404" in error
    
    @pytest.mark.asyncio
    async def test_initialization_and_cleanup(self, url_manager):
        """Test URL manager initialization and cleanup"""
        assert not url_manager.is_initialized()
        
        await url_manager.initialize()
        assert url_manager.is_initialized()
        assert url_manager.session is not None
        
        await url_manager.cleanup()
        assert not url_manager.is_initialized()
    
    def test_get_domain_stats(self, url_manager):
        """Test getting domain statistics"""
        # Add URLs from different domains
        url_manager.add_urls([
            "https://example.com/page1",
            "https://example.com/page2",
            "https://test.org/page1"
        ])
        
        # Simulate some processing
        url_manager.get_next_batch(2)
        
        domain_stats = url_manager.get_domain_stats()
        
        assert "example.com" in domain_stats
        assert "test.org" in domain_stats
        
        example_stats = domain_stats["example.com"]
        assert "request_count" in example_stats
        assert "rate_limit" in example_stats
        assert "consecutive_failures" in example_stats
        assert "in_backoff" in example_stats


if __name__ == "__main__":
    pytest.main([__file__])