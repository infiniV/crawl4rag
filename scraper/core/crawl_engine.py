"""
Crawl4AI Engine Implementation

This module provides the core web crawling functionality using crawl4ai with advanced features
including asynchronous crawling, JavaScript execution, session management, and concurrent processing.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urljoin, urlparse
import time
from dataclasses import dataclass

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.models import CrawlResult as Crawl4aiResult

from scraper.core.base import (
    CrawlEngineInterface, 
    CrawlResult, 
    CrawlingError,
    BaseComponent
)
from scraper.core.config import CrawlConfig
from scraper.core.logging import get_logger


@dataclass
class SessionInfo:
    """Session management information"""
    session_id: str
    cookies: Dict[str, str]
    headers: Dict[str, str]
    auth_token: Optional[str] = None
    created_at: float = 0.0
    last_used: float = 0.0


class CrawlEngine(CrawlEngineInterface):
    """
    Advanced crawl4ai engine implementation with support for:
    - Asynchronous crawling with configurable concurrency
    - JavaScript execution and lazy loading
    - Session management and authentication
    - File downloads and media handling
    - Rate limiting and error recovery
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Use standard logging for now, will be replaced by get_logger() after setup
        self.logger = logging.getLogger(__name__)
        self.crawl_config = CrawlConfig(**config.get('crawl', {}))
        
        # Crawler instances and configuration
        self.crawler: Optional[AsyncWebCrawler] = None
        self.browser_config: Optional[BrowserConfig] = None
        self.crawler_run_config: Optional[CrawlerRunConfig] = None
        
        # Session management
        self.sessions: Dict[str, SessionInfo] = {}
        self.session_timeout = config.get('session_timeout', 3600)  # 1 hour
        
        # Concurrency control
        self.max_concurrent = config.get('max_workers', 10)
        self.semaphore: Optional[asyncio.Semaphore] = None
        self.rate_limits: Dict[str, float] = {}  # domain -> last_request_time
        self.min_delay = config.get('rate_limit', 1.0)
        
        # Statistics
        self.stats = {
            'total_crawled': 0,
            'successful_crawls': 0,
            'failed_crawls': 0,
            'total_time': 0.0
        }

    async def initialize(self) -> None:
        """Initialize the crawl engine with browser and crawler configurations"""
        try:
            self.logger.info("Initializing crawl4ai engine...")
            
            # Set up browser configuration
            self.browser_config = BrowserConfig(
                headless=self.crawl_config.headless,
                accept_downloads=self.crawl_config.accept_downloads,
                # Enable file downloads and media handling
                downloads_path="./files",
                # Browser arguments for better performance and compatibility
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--allow-running-insecure-content",
                    "--disable-features=VizDisplayCompositor"
                ]
            )
            
            # Set up crawler run configuration
            self.crawler_run_config = CrawlerRunConfig(
                # JavaScript execution and interaction
                js_code="""
                // Wait for lazy-loaded content
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Trigger any lazy loading mechanisms
                const images = document.querySelectorAll('img[data-src]');
                images.forEach(img => {
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                    }
                });
                
                // Wait for images to load
                await new Promise(resolve => setTimeout(resolve, 2000));
                """,
                
                # Page interaction settings
                wait_for_images=self.crawl_config.wait_for_images,
                scan_full_page=self.crawl_config.scan_full_page,
                scroll_delay=self.crawl_config.scroll_delay,
                
                # Timeout settings
                page_timeout=self.crawl_config.timeout * 1000  # Convert to milliseconds
            )
            
            # Initialize the crawler
            self.crawler = AsyncWebCrawler(config=self.browser_config)
            # No need to call astart() - we'll use the crawler directly
            
            # Set up concurrency control
            self.semaphore = asyncio.Semaphore(self.max_concurrent)
            
            self._initialized = True
            self.logger.info(f"Crawl engine initialized with max_concurrent={self.max_concurrent}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize crawl engine: {e}")
            raise CrawlingError(f"Initialization failed: {e}")

    async def cleanup(self) -> None:
        """Clean up crawler resources"""
        try:
            if self.crawler:
                # Check if the crawler has a close method
                if hasattr(self.crawler, 'aclose'):
                    await self.crawler.aclose()
                elif hasattr(self.crawler, 'close'):
                    await self.crawler.close()
                self.crawler = None
            
            # Clear sessions
            self.sessions.clear()
            
            self.logger.info("Crawl engine cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def crawl_url(self, url: str, config: Dict[str, Any]) -> CrawlResult:
        """
        Crawl a single URL with advanced features
        
        Args:
            url: URL to crawl
            config: Additional configuration options
            
        Returns:
            CrawlResult with extracted content and metadata
        """
        if not self._initialized:
            raise CrawlingError("Crawl engine not initialized")
        
        start_time = time.time()
        domain = urlparse(url).netloc
        
        try:
            # Apply rate limiting
            await self._apply_rate_limit(domain)
            
            # Get session info if available
            session_info = config.get('session_info')
            
            # Prepare crawler configuration
            run_config = self._prepare_run_config(config, session_info)
            
            self.logger.debug(f"Starting crawl for: {url}")
            
            # Perform the crawl
            async with self.semaphore:
                # Use the crawler directly with the run config
                result = await self.crawler.arun(url=url, config=run_config)
            
            # Convert crawl4ai result to our format
            crawl_result = self._convert_result(result, url)
            
            # Update statistics
            self.stats['total_crawled'] += 1
            self.stats['successful_crawls'] += 1
            self.stats['total_time'] += time.time() - start_time
            
            self.logger.debug(f"Successfully crawled: {url}")
            return crawl_result
            
        except Exception as e:
            self.stats['total_crawled'] += 1
            self.stats['failed_crawls'] += 1
            self.stats['total_time'] += time.time() - start_time
            
            error_msg = f"Failed to crawl {url}: {e}"
            self.logger.error(error_msg)
            
            return CrawlResult(
                url=url,
                html="",
                markdown="",
                links=[],
                media=[],
                metadata={},
                success=False,
                error_message=error_msg
            )

    async def crawl_batch(self, urls: List[str], config: Dict[str, Any]) -> List[CrawlResult]:
        """
        Crawl multiple URLs concurrently with proper resource management
        
        Args:
            urls: List of URLs to crawl
            config: Configuration options
            
        Returns:
            List of CrawlResult objects
        """
        if not self._initialized:
            raise CrawlingError("Crawl engine not initialized")
        
        self.logger.info(f"Starting batch crawl of {len(urls)} URLs")
        
        # Create tasks for concurrent execution
        tasks = [
            self.crawl_url(url, config)
            for url in urls
        ]
        
        # Execute with proper error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = f"Exception during crawl: {result}"
                self.logger.error(error_msg)
                processed_results.append(CrawlResult(
                    url=urls[i],
                    html="",
                    markdown="",
                    links=[],
                    media=[],
                    metadata={},
                    success=False,
                    error_message=error_msg
                ))
            else:
                processed_results.append(result)
        
        successful = sum(1 for r in processed_results if r.success)
        self.logger.info(f"Batch crawl completed: {successful}/{len(urls)} successful")
        
        return processed_results

    def create_session(self, session_id: str, auth_config: Dict[str, Any]) -> SessionInfo:
        """
        Create a new session with authentication
        
        Args:
            session_id: Unique session identifier
            auth_config: Authentication configuration
            
        Returns:
            SessionInfo object
        """
        session_info = SessionInfo(
            session_id=session_id,
            cookies=auth_config.get('cookies', {}),
            headers=auth_config.get('headers', {}),
            auth_token=auth_config.get('auth_token'),
            created_at=time.time(),
            last_used=time.time()
        )
        
        self.sessions[session_id] = session_info
        self.logger.info(f"Created session: {session_id}")
        
        return session_info

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information by ID"""
        session = self.sessions.get(session_id)
        if session and time.time() - session.created_at < self.session_timeout:
            session.last_used = time.time()
            return session
        elif session:
            # Session expired
            del self.sessions[session_id]
            self.logger.info(f"Session expired: {session_id}")
        
        return None

    def cleanup_expired_sessions(self) -> None:
        """Remove expired sessions"""
        current_time = time.time()
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if current_time - session.created_at > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            self.logger.debug(f"Cleaned up expired session: {session_id}")

    def get_browser_config(self) -> Dict[str, Any]:
        """Get browser configuration"""
        if not self.browser_config:
            return {}
        
        return {
            'headless': self.browser_config.headless,
            'accept_downloads': self.browser_config.accept_downloads,
            'downloads_path': getattr(self.browser_config, 'downloads_path', './files'),
            'browser_args': getattr(self.browser_config, 'browser_args', [])
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get crawling statistics"""
        return {
            **self.stats,
            'active_sessions': len(self.sessions),
            'success_rate': (
                self.stats['successful_crawls'] / max(self.stats['total_crawled'], 1)
            ) * 100,
            'average_time': (
                self.stats['total_time'] / max(self.stats['total_crawled'], 1)
            )
        }

    async def _apply_rate_limit(self, domain: str) -> None:
        """Apply rate limiting per domain"""
        if domain in self.rate_limits:
            elapsed = time.time() - self.rate_limits[domain]
            if elapsed < self.min_delay:
                await asyncio.sleep(self.min_delay - elapsed)
        
        self.rate_limits[domain] = time.time()

    def _prepare_run_config(self, config: Dict[str, Any], session_info: Optional[SessionInfo]) -> CrawlerRunConfig:
        """Prepare crawler run configuration with session and custom settings"""
        # Start with base configuration
        run_config_dict = {
            'js_code': self.crawler_run_config.js_code,
            'wait_for_images': self.crawler_run_config.wait_for_images,
            'scan_full_page': self.crawler_run_config.scan_full_page,
            'scroll_delay': self.crawler_run_config.scroll_delay,
            'page_timeout': self.crawler_run_config.page_timeout
        }
        
        # Add session-specific configuration
        if session_info:
            # For session-based headers and cookies, we'll need to handle them differently
            # since CrawlerRunConfig doesn't directly support headers
            if session_info.cookies:
                # Store cookies for later use with browser context
                run_config_dict['shared_data'] = {'session_cookies': session_info.cookies}
        
        # Override with any custom configuration
        custom_js = config.get('custom_js_code')
        if custom_js:
            run_config_dict['js_code'] = custom_js
        
        if 'page_timeout' in config:
            run_config_dict['page_timeout'] = config['page_timeout'] * 1000
        
        return CrawlerRunConfig(**run_config_dict)

    def _convert_result(self, crawl4ai_result: Crawl4aiResult, url: str) -> CrawlResult:
        """Convert crawl4ai result to our CrawlResult format"""
        try:
            # Extract links from the result
            links = []
            if hasattr(crawl4ai_result, 'links') and crawl4ai_result.links:
                for link_data in crawl4ai_result.links:
                    if isinstance(link_data, dict) and 'href' in link_data:
                        # Convert relative URLs to absolute
                        href = link_data['href']
                        if href.startswith('http'):
                            links.append(href)
                        else:
                            links.append(urljoin(url, href))
            
            # Extract media information
            media = []
            if hasattr(crawl4ai_result, 'media') and crawl4ai_result.media:
                for media_item in crawl4ai_result.media:
                    if isinstance(media_item, dict):
                        # Convert relative URLs to absolute
                        if 'src' in media_item:
                            src = media_item['src']
                            if not src.startswith('http'):
                                media_item['src'] = urljoin(url, src)
                        media.append(media_item)
            
            # Prepare metadata
            metadata = {
                'title': getattr(crawl4ai_result, 'title', ''),
                'description': getattr(crawl4ai_result, 'description', ''),
                'keywords': getattr(crawl4ai_result, 'keywords', []),
                'language': getattr(crawl4ai_result, 'language', ''),
                'crawl_timestamp': time.time(),
                'response_headers': getattr(crawl4ai_result, 'response_headers', {}),
                'status_code': getattr(crawl4ai_result, 'status_code', 200)
            }
            
            return CrawlResult(
                url=url,
                html=crawl4ai_result.html or "",
                markdown=crawl4ai_result.markdown or "",
                links=links,
                media=media,
                metadata=metadata,
                success=crawl4ai_result.success,
                error_message=crawl4ai_result.error_message
            )
            
        except Exception as e:
            self.logger.error(f"Error converting crawl result for {url}: {e}")
            return CrawlResult(
                url=url,
                html="",
                markdown="",
                links=[],
                media=[],
                metadata={},
                success=False,
                error_message=f"Result conversion failed: {e}"
            )