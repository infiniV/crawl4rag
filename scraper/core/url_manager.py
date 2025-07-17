"""
URL Management and Validation System for Production Web Scraper

Implements URL validation, normalization, accessibility checking, queue management
with priority and deduplication, domain-based rate limiting, and discovered URL
handling for deep crawling.

Requirements covered:
- 1.3: URL validation and accessibility checking
- 1.4: Concurrent processing with rate limiting
- 1.5: Authentication and session management support
- 2.1: Deep scanning with link following
- 2.3: Dynamic URL discovery and queue management
"""

import asyncio
import time
import hashlib
import logging
from typing import List, Dict, Set, Optional, Tuple, Any
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
import validators
from .base import URLManagerInterface, ScraperError


class URLPriority(Enum):
    """Priority levels for URL processing"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class URLStatus(Enum):
    """Status of URLs in the processing queue"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class URLInfo:
    """Information about a URL in the processing queue"""
    url: str
    normalized_url: str
    domain: str
    priority: URLPriority = URLPriority.MEDIUM
    depth: int = 0
    discovered_from: Optional[str] = None
    status: URLStatus = URLStatus.PENDING
    retry_count: int = 0
    last_attempt: Optional[datetime] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainRateLimit:
    """Rate limiting information for a domain"""
    domain: str
    last_request: Optional[datetime] = None
    request_count: int = 0
    rate_limit: float = 1.0  # seconds between requests
    backoff_until: Optional[datetime] = None
    consecutive_failures: int = 0


class URLValidationError(ScraperError):
    """URL validation specific errors"""
    pass


class URLManager(URLManagerInterface):
    """
    Comprehensive URL management system with validation, normalization,
    queue management, rate limiting, and deep crawling support.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.max_depth = config.get('max_depth', 3)
        self.rate_limit = config.get('rate_limit', 1.0)
        self.max_retries = config.get('max_retries', 3)
        self.timeout = config.get('timeout', 30)
        self.follow_external_links = config.get('follow_external_links', False)
        self.respect_robots_txt = config.get('respect_robots_txt', True)
        
        # URL storage and management
        self.url_queue: deque[URLInfo] = deque()
        self.url_set: Set[str] = set()  # For deduplication
        self.processed_urls: Dict[str, URLInfo] = {}
        self.failed_urls: Dict[str, URLInfo] = {}
        
        # Domain-based rate limiting
        self.domain_limits: Dict[str, DomainRateLimit] = {}
        
        # Statistics
        self.stats = {
            'total_urls': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'discovered': 0
        }
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # URL patterns to skip
        self.skip_patterns = [
            r'\.pdf$', r'\.doc$', r'\.docx$', r'\.xls$', r'\.xlsx$',
            r'\.zip$', r'\.rar$', r'\.tar$', r'\.gz$',
            r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$', r'\.svg$',
            r'\.mp4$', r'\.avi$', r'\.mov$', r'\.wmv$',
            r'\.mp3$', r'\.wav$', r'\.ogg$',
            r'mailto:', r'tel:', r'ftp:', r'javascript:'
        ]
    
    async def initialize(self) -> None:
        """Initialize the URL manager"""
        if self._initialized:
            return
        
        # Create HTTP session with proper configuration
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=10,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'Production-Web-Scraper/1.0 (+https://farmovation.com/bot)'
            }
        )
        
        self._initialized = True
        self.logger.info("URL Manager initialized successfully")
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.session:
            await self.session.close()
        self._initialized = False
        self.logger.info("URL Manager cleaned up")
    
    def validate_urls(self, urls: List[str]) -> List[str]:
        """
        Validate and filter URLs, returning only valid ones.
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            List of valid, normalized URLs
        """
        valid_urls = []
        
        for url in urls:
            try:
                normalized_url = self._normalize_url(url)
                if self._is_valid_url(normalized_url):
                    valid_urls.append(normalized_url)
                    self.logger.debug(f"URL validated: {normalized_url}")
                else:
                    self.logger.warning(f"URL validation failed: {url}")
            except Exception as e:
                self.logger.error(f"Error validating URL {url}: {e}")
        
        self.logger.info(f"Validated {len(valid_urls)} out of {len(urls)} URLs")
        return valid_urls
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing fragments, sorting query parameters,
        and ensuring consistent format.
        """
        # Parse URL
        parsed = urlparse(url.strip())
        
        # Ensure scheme
        if not parsed.scheme:
            parsed = urlparse(f"https://{url.strip()}")
        
        # Normalize domain to lowercase
        netloc = parsed.netloc.lower()
        
        # Remove default ports
        if netloc.endswith(':80') and parsed.scheme == 'http':
            netloc = netloc[:-3]
        elif netloc.endswith(':443') and parsed.scheme == 'https':
            netloc = netloc[:-4]
        
        # Normalize path
        path = parsed.path or '/'
        if path != '/' and path.endswith('/'):
            path = path[:-1]
        
        # Sort query parameters for consistency
        query = ''
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            sorted_params = sorted(params.items())
            query_parts = []
            for key, values in sorted_params:
                for value in values:
                    query_parts.append(f"{key}={value}")
            query = '&'.join(query_parts)
        
        # Reconstruct URL without fragment
        normalized = urlunparse((
            parsed.scheme,
            netloc,
            path,
            parsed.params,
            query,
            ''  # Remove fragment
        ))
        
        return normalized
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and should be processed"""
        # Basic URL validation
        if not validators.url(url):
            return False
        
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Check for skip patterns
        import re
        for pattern in self.skip_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Check domain restrictions if configured
        allowed_domains = self.config.get('allowed_domains', [])
        if allowed_domains:
            domain = parsed.netloc.lower()
            if not any(domain.endswith(allowed) for allowed in allowed_domains):
                return False
        
        return True
    
    async def check_url_accessibility(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Check if URL is accessible by making a HEAD request.
        
        Returns:
            Tuple of (is_accessible, error_message)
        """
        if not self.session:
            await self.initialize()
        
        try:
            async with self.session.head(url, allow_redirects=True) as response:
                if response.status < 400:
                    return True, None
                else:
                    return False, f"HTTP {response.status}: {response.reason}"
        except asyncio.TimeoutError:
            return False, "Request timeout"
        except aiohttp.ClientError as e:
            return False, f"Client error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def add_urls(self, urls: List[str], priority: URLPriority = URLPriority.MEDIUM, 
                 depth: int = 0, discovered_from: Optional[str] = None) -> int:
        """
        Add URLs to the processing queue with deduplication.
        
        Args:
            urls: List of URLs to add
            priority: Priority level for processing
            depth: Current crawling depth
            discovered_from: URL that discovered these URLs
            
        Returns:
            Number of new URLs added
        """
        added_count = 0
        
        for url in urls:
            try:
                normalized_url = self._normalize_url(url)
                
                # Skip if already processed or in queue
                if normalized_url in self.url_set:
                    continue
                
                # Skip if depth exceeds limit
                if depth > self.max_depth:
                    continue
                
                # Validate URL
                if not self._is_valid_url(normalized_url):
                    continue
                
                # Create URL info
                domain = urlparse(normalized_url).netloc
                url_info = URLInfo(
                    url=url,
                    normalized_url=normalized_url,
                    domain=domain,
                    priority=priority,
                    depth=depth,
                    discovered_from=discovered_from
                )
                
                # Add to queue and set
                self.url_queue.append(url_info)
                self.url_set.add(normalized_url)
                added_count += 1
                
                # Initialize domain rate limiting if needed
                if domain not in self.domain_limits:
                    self.domain_limits[domain] = DomainRateLimit(
                        domain=domain,
                        rate_limit=self.rate_limit
                    )
                
                self.logger.debug(f"Added URL to queue: {normalized_url} (depth: {depth})")
                
            except Exception as e:
                self.logger.error(f"Error adding URL {url}: {e}")
        
        self.stats['total_urls'] += added_count
        if depth > 0:
            self.stats['discovered'] += added_count
        
        self.logger.info(f"Added {added_count} new URLs to queue")
        return added_count
    
    def add_discovered_urls(self, urls: List[str], depth: int) -> None:
        """Add newly discovered URLs to processing queue"""
        self.add_urls(urls, priority=URLPriority.LOW, depth=depth)
    
    def get_next_batch(self, batch_size: int) -> List[str]:
        """
        Get next batch of URLs to process, respecting rate limits and priorities.
        
        Args:
            batch_size: Maximum number of URLs to return
            
        Returns:
            List of URLs ready for processing
        """
        ready_urls = []
        current_time = datetime.now()
        
        # Sort queue by priority
        sorted_queue = sorted(self.url_queue, key=lambda x: x.priority.value)
        
        for url_info in sorted_queue:
            if len(ready_urls) >= batch_size:
                break
            
            # Skip if already processing or completed
            if url_info.status != URLStatus.PENDING:
                continue
            
            # Check domain rate limiting
            domain_limit = self.domain_limits.get(url_info.domain)
            if domain_limit:
                # Check if domain is in backoff
                if (domain_limit.backoff_until and 
                    current_time < domain_limit.backoff_until):
                    continue
                
                # Check rate limit
                if (domain_limit.last_request and
                    (current_time - domain_limit.last_request).total_seconds() < domain_limit.rate_limit):
                    continue
            
            # Mark as processing and add to batch
            url_info.status = URLStatus.PROCESSING
            ready_urls.append(url_info.normalized_url)
            
            # Update domain rate limiting
            if domain_limit:
                domain_limit.last_request = current_time
                domain_limit.request_count += 1
        
        self.logger.info(f"Retrieved batch of {len(ready_urls)} URLs for processing")
        return ready_urls
    
    def mark_processed(self, url: str, success: bool, error_message: Optional[str] = None,
                      processing_time: float = 0.0) -> None:
        """
        Mark URL as processed and update statistics.
        
        Args:
            url: URL that was processed
            success: Whether processing was successful
            error_message: Error message if processing failed
            processing_time: Time taken to process the URL
        """
        # Find URL info in queue
        url_info = None
        for info in self.url_queue:
            if info.normalized_url == url:
                url_info = info
                break
        
        if not url_info:
            self.logger.warning(f"URL not found in queue: {url}")
            return
        
        # Update URL info
        url_info.processing_time = processing_time
        url_info.error_message = error_message
        
        if success:
            url_info.status = URLStatus.COMPLETED
            self.processed_urls[url] = url_info
            self.stats['processed'] += 1
            
            # Reset domain failure count on success
            domain_limit = self.domain_limits.get(url_info.domain)
            if domain_limit:
                domain_limit.consecutive_failures = 0
                domain_limit.backoff_until = None
            
            self.logger.debug(f"Marked URL as completed: {url}")
        else:
            url_info.retry_count += 1
            
            # Check if we should retry
            if url_info.retry_count < self.max_retries:
                url_info.status = URLStatus.PENDING
                url_info.last_attempt = datetime.now()
                self.logger.info(f"URL will be retried ({url_info.retry_count}/{self.max_retries}): {url}")
            else:
                url_info.status = URLStatus.FAILED
                self.failed_urls[url] = url_info
                self.stats['failed'] += 1
                
                # Update domain backoff on repeated failures
                domain_limit = self.domain_limits.get(url_info.domain)
                if domain_limit:
                    domain_limit.consecutive_failures += 1
                    if domain_limit.consecutive_failures >= 3:
                        # Exponential backoff: 2^failures minutes
                        backoff_minutes = 2 ** min(domain_limit.consecutive_failures - 2, 6)
                        domain_limit.backoff_until = datetime.now() + timedelta(minutes=backoff_minutes)
                        self.logger.warning(f"Domain {url_info.domain} in backoff for {backoff_minutes} minutes")
                
                self.logger.error(f"Marked URL as failed after {url_info.retry_count} attempts: {url}")
    
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status and statistics"""
        status_counts = defaultdict(int)
        
        for url_info in self.url_queue:
            status_counts[url_info.status.value] += 1
        
        return {
            'total_urls': self.stats['total_urls'],
            'pending': status_counts['pending'],
            'processing': status_counts['processing'],
            'completed': self.stats['processed'],
            'failed': self.stats['failed'],
            'skipped': self.stats['skipped'],
            'discovered': self.stats['discovered'],
            'queue_size': len(self.url_queue),
            'domains_tracked': len(self.domain_limits)
        }
    
    def get_domain_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics per domain"""
        domain_stats = {}
        
        for domain, limit_info in self.domain_limits.items():
            domain_stats[domain] = {
                'request_count': limit_info.request_count,
                'rate_limit': limit_info.rate_limit,
                'consecutive_failures': limit_info.consecutive_failures,
                'in_backoff': limit_info.backoff_until is not None and datetime.now() < limit_info.backoff_until,
                'backoff_until': limit_info.backoff_until.isoformat() if limit_info.backoff_until else None
            }
        
        return domain_stats
    
    def extract_links_from_content(self, html_content: str, base_url: str) -> List[str]:
        """
        Extract links from HTML content for deep crawling.
        
        Args:
            html_content: HTML content to extract links from
            base_url: Base URL for resolving relative links
            
        Returns:
            List of discovered URLs
        """
        from bs4 import BeautifulSoup
        import re
        
        discovered_urls = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            base_domain = urlparse(base_url).netloc
            
            # Extract links from <a> tags
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                if not href or href.startswith('#'):
                    continue
                
                # Resolve relative URLs
                absolute_url = urljoin(base_url, href)
                
                # Check if we should follow external links
                link_domain = urlparse(absolute_url).netloc
                if not self.follow_external_links and link_domain != base_domain:
                    continue
                
                discovered_urls.append(absolute_url)
            
            # Extract links from other elements if needed
            for element in soup.find_all(['area', 'link'], href=True):
                href = element['href'].strip()
                if href and not href.startswith('#'):
                    absolute_url = urljoin(base_url, href)
                    discovered_urls.append(absolute_url)
            
            self.logger.debug(f"Extracted {len(discovered_urls)} links from {base_url}")
            
        except Exception as e:
            self.logger.error(f"Error extracting links from {base_url}: {e}")
        
        return discovered_urls
    
    def get_failed_urls(self) -> List[Dict[str, Any]]:
        """Get list of failed URLs with error information"""
        failed_list = []
        
        for url, url_info in self.failed_urls.items():
            failed_list.append({
                'url': url,
                'domain': url_info.domain,
                'retry_count': url_info.retry_count,
                'error_message': url_info.error_message,
                'last_attempt': url_info.last_attempt.isoformat() if url_info.last_attempt else None,
                'depth': url_info.depth,
                'discovered_from': url_info.discovered_from
            })
        
        return failed_list
    
    def reset_failed_urls(self) -> int:
        """Reset failed URLs for retry"""
        reset_count = 0
        
        for url, url_info in self.failed_urls.items():
            url_info.status = URLStatus.PENDING
            url_info.retry_count = 0
            url_info.error_message = None
            url_info.last_attempt = None
            reset_count += 1
        
        # Move back to main stats
        self.stats['failed'] -= reset_count
        self.failed_urls.clear()
        
        self.logger.info(f"Reset {reset_count} failed URLs for retry")
        return reset_count
    
    def clear_queue(self) -> None:
        """Clear the URL queue and reset statistics"""
        self.url_queue.clear()
        self.url_set.clear()
        self.processed_urls.clear()
        self.failed_urls.clear()
        self.domain_limits.clear()
        
        self.stats = {
            'total_urls': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'discovered': 0
        }
        
        self.logger.info("URL queue cleared")