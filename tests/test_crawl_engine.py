"""
Tests for CrawlEngine implementation

Tests the crawl4ai integration with advanced features including
session management, concurrent crawling, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from scraper.core.crawl_engine import CrawlEngine, SessionInfo
from scraper.core.base import CrawlResult, CrawlingError


class TestCrawlEngine:
    """Test suite for CrawlEngine"""
    
    @pytest.fixture
    def engine_config(self):
        """Basic engine configuration for testing"""
        return {
            'crawl': {
                'headless': True,
                'wait_for_images': True,
                'scan_full_page': True,
                'scroll_delay': 0.5,
                'accept_downloads': True,
                'timeout': 30
            },
            'max_workers': 5,
            'rate_limit': 0.1,  # Faster for testing
            'session_timeout': 300
        }
    
    @pytest.fixture
    def crawl_engine(self, engine_config):
        """Create CrawlEngine instance for testing"""
        return CrawlEngine(engine_config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, crawl_engine):
        """Test engine initialization"""
        with patch('scraper.core.crawl_engine.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value = mock_crawler
            
            await crawl_engine.initialize()
            
            assert crawl_engine.is_initialized()
            assert crawl_engine.crawler is not None
            assert crawl_engine.semaphore is not None
            mock_crawler.astart.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, crawl_engine):
        """Test engine cleanup"""
        with patch('scraper.core.crawl_engine.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value = mock_crawler
            
            await crawl_engine.initialize()
            await crawl_engine.cleanup()
            
            mock_crawler.aclose.assert_called_once()
            assert len(crawl_engine.sessions) == 0
    
    @pytest.mark.asyncio
    async def test_crawl_single_url_success(self, crawl_engine):
        """Test successful single URL crawling"""
        with patch('scraper.core.crawl_engine.AsyncWebCrawler') as mock_crawler_class:
            # Mock crawl4ai result
            mock_result = Mock()
            mock_result.html = "<html><body>Test content</body></html>"
            mock_result.markdown = "# Test content"
            mock_result.links = [{"href": "https://example.com/page1"}]
            mock_result.media = [{"src": "image.jpg", "alt": "test image"}]
            mock_result.title = "Test Page"
            mock_result.success = True
            mock_result.error_message = None
            
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value = mock_crawler
            
            await crawl_engine.initialize()
            
            result = await crawl_engine.crawl_url("https://example.com", {})
            
            assert isinstance(result, CrawlResult)
            assert result.success
            assert result.url == "https://example.com"
            assert result.html == "<html><body>Test content</body></html>"
            assert result.markdown == "# Test content"
            assert len(result.links) == 1
            assert len(result.media) == 1
            assert result.metadata['title'] == "Test Page"
    
    @pytest.mark.asyncio
    async def test_crawl_single_url_failure(self, crawl_engine):
        """Test failed single URL crawling"""
        with patch('scraper.core.crawl_engine.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.side_effect = Exception("Network error")
            mock_crawler_class.return_value = mock_crawler
            
            await crawl_engine.initialize()
            
            result = await crawl_engine.crawl_url("https://example.com", {})
            
            assert isinstance(result, CrawlResult)
            assert not result.success
            assert "Network error" in result.error_message
            assert result.html == ""
            assert result.markdown == ""
    
    @pytest.mark.asyncio
    async def test_crawl_batch_urls(self, crawl_engine):
        """Test batch URL crawling"""
        with patch('scraper.core.crawl_engine.AsyncWebCrawler') as mock_crawler_class:
            # Mock successful results
            mock_result1 = Mock()
            mock_result1.html = "<html>Page 1</html>"
            mock_result1.markdown = "# Page 1"
            mock_result1.links = []
            mock_result1.media = []
            mock_result1.success = True
            mock_result1.error_message = None
            
            mock_result2 = Mock()
            mock_result2.html = "<html>Page 2</html>"
            mock_result2.markdown = "# Page 2"
            mock_result2.links = []
            mock_result2.media = []
            mock_result2.success = True
            mock_result2.error_message = None
            
            mock_crawler = AsyncMock()
            mock_crawler.arun.side_effect = [mock_result1, mock_result2]
            mock_crawler_class.return_value = mock_crawler
            
            await crawl_engine.initialize()
            
            urls = ["https://example.com/page1", "https://example.com/page2"]
            results = await crawl_engine.crawl_batch(urls, {})
            
            assert len(results) == 2
            assert all(isinstance(r, CrawlResult) for r in results)
            assert all(r.success for r in results)
            assert results[0].markdown == "# Page 1"
            assert results[1].markdown == "# Page 2"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, crawl_engine):
        """Test rate limiting functionality"""
        with patch('scraper.core.crawl_engine.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value = mock_crawler
            
            await crawl_engine.initialize()
            
            # Test rate limiting for same domain
            import time
            start_time = time.time()
            
            await crawl_engine._apply_rate_limit("example.com")
            await crawl_engine._apply_rate_limit("example.com")
            
            elapsed = time.time() - start_time
            # Should have waited at least the minimum delay
            assert elapsed >= crawl_engine.min_delay * 0.9  # Allow some tolerance
    
    def test_session_management(self, crawl_engine):
        """Test session creation and management"""
        auth_config = {
            'cookies': {'session_id': 'abc123'},
            'headers': {'X-Custom-Header': 'value'},
            'auth_token': 'bearer_token_123'
        }
        
        # Create session
        session = crawl_engine.create_session("test_session", auth_config)
        
        assert isinstance(session, SessionInfo)
        assert session.session_id == "test_session"
        assert session.cookies == {'session_id': 'abc123'}
        assert session.headers == {'X-Custom-Header': 'value'}
        assert session.auth_token == "bearer_token_123"
        
        # Retrieve session
        retrieved_session = crawl_engine.get_session("test_session")
        assert retrieved_session is not None
        assert retrieved_session.session_id == "test_session"
        
        # Test non-existent session
        non_existent = crawl_engine.get_session("non_existent")
        assert non_existent is None
    
    def test_session_expiration(self, crawl_engine):
        """Test session expiration handling"""
        # Create session with very short timeout
        crawl_engine.session_timeout = 0.1
        
        auth_config = {'cookies': {}, 'headers': {}}
        session = crawl_engine.create_session("expire_test", auth_config)
        
        # Wait for expiration
        import time
        time.sleep(0.2)
        
        # Session should be expired
        expired_session = crawl_engine.get_session("expire_test")
        assert expired_session is None
        assert "expire_test" not in crawl_engine.sessions
    
    def test_cleanup_expired_sessions(self, crawl_engine):
        """Test cleanup of expired sessions"""
        crawl_engine.session_timeout = 0.1
        
        # Create multiple sessions
        for i in range(3):
            crawl_engine.create_session(f"session_{i}", {'cookies': {}, 'headers': {}})
        
        assert len(crawl_engine.sessions) == 3
        
        # Wait for expiration
        import time
        time.sleep(0.2)
        
        # Cleanup expired sessions
        crawl_engine.cleanup_expired_sessions()
        
        assert len(crawl_engine.sessions) == 0
    
    def test_statistics_tracking(self, crawl_engine):
        """Test statistics tracking"""
        initial_stats = crawl_engine.get_stats()
        
        assert initial_stats['total_crawled'] == 0
        assert initial_stats['successful_crawls'] == 0
        assert initial_stats['failed_crawls'] == 0
        assert initial_stats['success_rate'] == 0.0
        
        # Simulate some crawling activity
        crawl_engine.stats['total_crawled'] = 10
        crawl_engine.stats['successful_crawls'] = 8
        crawl_engine.stats['failed_crawls'] = 2
        crawl_engine.stats['total_time'] = 50.0
        
        stats = crawl_engine.get_stats()
        assert stats['total_crawled'] == 10
        assert stats['successful_crawls'] == 8
        assert stats['failed_crawls'] == 2
        assert stats['success_rate'] == 80.0
        assert stats['average_time'] == 5.0
    
    @pytest.mark.asyncio
    async def test_crawl_without_initialization(self, crawl_engine):
        """Test crawling without proper initialization"""
        with pytest.raises(CrawlingError, match="not initialized"):
            await crawl_engine.crawl_url("https://example.com", {})
    
    def test_prepare_run_config_with_session(self, crawl_engine):
        """Test run configuration preparation with session"""
        # Create a session
        auth_config = {
            'cookies': {'auth': 'token123'},
            'headers': {'X-API-Key': 'key123'},
            'auth_token': 'bearer_abc'
        }
        session = crawl_engine.create_session("test", auth_config)
        
        # Initialize crawler config (mock)
        crawl_engine.crawler_run_config = Mock()
        crawl_engine.crawler_run_config.js_code = "console.log('test');"
        crawl_engine.crawler_run_config.wait_for_images = True
        crawl_engine.crawler_run_config.scan_full_page = True
        crawl_engine.crawler_run_config.scroll_delay = 0.5
        crawl_engine.crawler_run_config.extract_media = True
        crawl_engine.crawler_run_config.extract_links = True
        crawl_engine.crawler_run_config.page_timeout = 30000
        crawl_engine.crawler_run_config.headers = {'User-Agent': 'test'}
        
        config = {'session_info': session}
        run_config = crawl_engine._prepare_run_config(config, session)
        
        # Verify session data is included in shared_data
        assert hasattr(run_config, 'shared_data')
        assert run_config.shared_data is not None
        assert 'session_cookies' in run_config.shared_data
        assert run_config.shared_data['session_cookies'] == {'auth': 'token123'}
    
    def test_convert_result_with_relative_urls(self, crawl_engine):
        """Test result conversion with relative URL handling"""
        # Mock crawl4ai result with relative URLs
        mock_result = Mock()
        mock_result.html = "<html>Test</html>"
        mock_result.markdown = "# Test"
        mock_result.links = [
            {"href": "/relative/path"},
            {"href": "https://absolute.com/path"}
        ]
        mock_result.media = [
            {"src": "/images/test.jpg", "alt": "test"},
            {"src": "https://cdn.example.com/image.png"}
        ]
        mock_result.title = "Test Page"
        mock_result.success = True
        mock_result.error_message = None
        
        base_url = "https://example.com/page"
        result = crawl_engine._convert_result(mock_result, base_url)
        
        # Check that relative URLs are converted to absolute
        assert "https://example.com/relative/path" in result.links
        assert "https://absolute.com/path" in result.links
        
        # Check media URL conversion
        media_srcs = [item['src'] for item in result.media]
        assert "https://example.com/images/test.jpg" in media_srcs
        assert "https://cdn.example.com/image.png" in media_srcs


@pytest.mark.asyncio
async def test_integration_crawl_engine():
    """Integration test for crawl engine with real configuration"""
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
        'rate_limit': 0.1
    }
    
    engine = CrawlEngine(config)
    
    # Test without actual network calls
    with patch('scraper.core.crawl_engine.AsyncWebCrawler') as mock_crawler_class:
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler
        
        await engine.initialize()
        
        # Verify initialization
        assert engine.is_initialized()
        assert engine.max_concurrent == 2
        assert engine.min_delay == 0.1
        
        await engine.cleanup()