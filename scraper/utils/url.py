"""
URL Utilities for Production Web Scraper

Provides URL validation, normalization, and management functions.
Implements URL queue management with priority and deduplication,
domain-based rate limiting, and discovered URL handling for deep crawling.
"""

import re
import time
import asyncio
import aiohttp
import logging
import hashlib
import urllib.robotparser
from typing import List, Dict, Any, Set, Optional, Tuple, Union
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs, urlencode
import tldextract
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from heapq import heappush, heappop

from scraper.core.base import URLManagerInterface, ScraperError
from scraper.core.logging import get_logger


class URLValidationError(ScraperError):
    """Error raised when URL validation fails"""
    pass


class URLAccessibilityError(ScraperError):
    """Error raised when URL accessibility check fails"""
    pass


class URLManager(URLManagerInterface):
    """
    Implementation of URL manager with advanced features:
    - URL validation, normalization, and accessibility checking
    - Priority-based queue management with deduplication
    - Domain-based rate limiting and processing coordination
    - Discovered URL handling for deep crawling
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger()
        
        # Configuration
        self.max_depth = config.get('max_depth', 3)
        self.rate_limit = config.get('rate_limit', 1.0)  # seconds between requests per domain
        self.accessibility_timeout = config.get('accessibility_timeout', 10)  # seconds
        self.check_accessibility = config.get('check_accessibility', True)
        self.follow_redirects = config.get('follow_redirects', True)
        self.respect_robots_txt = config.get('respect_robots_txt', True)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 5)  # seconds
        self.priority_domains = config.get('priority_domains', [])
        self.excluded_domains = config.get('excluded_domains', [])
        self.excluded_patterns = config.get('excluded_patterns', [
            r'\.(jpg|jpeg|png|gif|css|js|ico|svg)$',
            r'(calendar|login|logout|signin|signout|register|subscribe|comment)',
            r'(facebook\.com|twitter\.com|instagram\.com|linkedin\.com)'
        ])
        
        # State
        self.processed_urls: Set[str] = set()
        self.url_queue: Dict[str, Dict[str, Any]] = {}
        self.domain_queues: Dict[str, List[str]] = defaultdict(list)
        self.domain_last_access: Dict[str, datetime] = {}
        self.domain_robots_rules: Dict[str, Any] = {}
        self.url_accessibility_cache: Dict[str, Tuple[bool, datetime]] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.url_fingerprints: Set[str] = set()  # For content-based deduplication
    
    async def initialize(self) -> None:
        """Initialize the component"""
        self.logger.info("Initializing URL manager")
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.accessibility_timeout),
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; ProductionWebScraper/1.0; +https://farmovation.com/bot)'
            }
        )
        self._initialized = True
        self.logger.info("URL manager initialized")
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Cleaning up URL manager")
        if self.session:
            await self.session.close()
        self.logger.info("URL manager cleanup completed")
    
    def validate_urls(self, urls: List[str]) -> List[str]:
        """
        Validate and filter URLs
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            List of valid URLs
        """
        valid_urls = []
        
        for url in urls:
            # Basic URL validation
            if not url or not isinstance(url, str):
                self.logger.warning(f"Invalid URL: {url}")
                continue
            
            # Normalize URL
            normalized_url = self._normalize_url(url)
            if not normalized_url:
                self.logger.warning(f"Failed to normalize URL: {url}")
                continue
            
            # Check if already processed
            if normalized_url in self.processed_urls:
                self.logger.info(f"URL already processed: {normalized_url}")
                continue
            
            # Check excluded patterns
            if self._is_excluded(normalized_url):
                self.logger.info(f"URL excluded by pattern: {normalized_url}")
                continue
            
            # Add to valid URLs
            valid_urls.append(normalized_url)
            
            # Add to URL queue with priority 0 (highest)
            self._add_to_queue(normalized_url, 0, priority=0)
        
        return valid_urls
    
    async def check_url_accessibility(self, url: str) -> bool:
        """
        Check if URL is accessible
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is accessible, False otherwise
        """
        # Check cache first
        if url in self.url_accessibility_cache:
            is_accessible, timestamp = self.url_accessibility_cache[url]
            # Cache valid for 1 hour
            if datetime.now() - timestamp < timedelta(hours=1):
                return is_accessible
        
        if not self.session:
            await self.initialize()
        
        try:
            # Respect rate limiting
            domain = self._extract_domain(url)
            await self._respect_rate_limit(domain)
            
            # Try to access the URL
            async with self.session.head(
                url, 
                allow_redirects=self.follow_redirects,
                ssl=False  # Ignore SSL errors
            ) as response:
                is_accessible = 200 <= response.status < 400
                
                # Update cache
                self.url_accessibility_cache[url] = (is_accessible, datetime.now())
                
                if not is_accessible:
                    self.logger.warning(f"URL not accessible: {url} (Status: {response.status})")
                
                return is_accessible
                
        except Exception as e:
            self.logger.warning(f"Error checking URL accessibility {url}: {e}")
            # Update cache with negative result
            self.url_accessibility_cache[url] = (False, datetime.now())
            return False
    
    def add_discovered_urls(self, urls: List[str], depth: int) -> None:
        """
        Add newly discovered URLs to processing queue
        
        Args:
            urls: List of discovered URLs
            depth: Current depth level
        """
        if depth >= self.max_depth:
            self.logger.debug(f"Max depth reached ({self.max_depth}), not adding discovered URLs")
            return
        
        added_count = 0
        for url in urls:
            # Normalize URL
            normalized_url = self._normalize_url(url)
            if not normalized_url:
                continue
            
            # Check if already processed or in queue
            if normalized_url in self.processed_urls or normalized_url in self.url_queue:
                continue
            
            # Check excluded patterns
            if self._is_excluded(normalized_url):
                continue
            
            # Calculate priority based on domain and depth
            priority = self._calculate_priority(normalized_url, depth)
            
            # Add to URL queue
            self._add_to_queue(normalized_url, depth + 1, priority)
            added_count += 1
        
        if added_count > 0:
            self.logger.info(f"Added {added_count} discovered URLs at depth {depth+1}")
    
    def get_next_batch(self, batch_size: int) -> List[str]:
        """
        Get next batch of URLs to process with domain-based rate limiting
        
        Args:
            batch_size: Number of URLs to return
            
        Returns:
            List of URLs to process
        """
        batch = []
        domains_in_batch = set()
        max_per_domain = max(1, batch_size // 4)  # Limit URLs per domain to 25% of batch size
        
        # Get URLs from queue, sorted by priority and then by depth and add time
        queue_items = list(self.url_queue.items())
        queue_items.sort(key=lambda x: (x[1]['priority'], x[1]['depth'], x[1]['added']))
        
        for url, info in queue_items:
            domain = info['domain']
            
            # Limit URLs per domain to prevent overwhelming a single domain
            if domain in domains_in_batch and list(domains_in_batch).count(domain) >= max_per_domain:
                continue
            
            batch.append(url)
            domains_in_batch.add(domain)
            
            # Remove from queue
            del self.url_queue[url]
            
            if len(batch) >= batch_size:
                break
        
        return batch
    
    def mark_processed(self, url: str, success: bool) -> None:
        """
        Mark URL as processed
        
        Args:
            url: URL to mark
            success: Whether processing was successful
        """
        normalized_url = self._normalize_url(url)
        if normalized_url:
            self.processed_urls.add(normalized_url)
            
            # Remove from queue if present
            if normalized_url in self.url_queue:
                del self.url_queue[normalized_url]
            
            # Update domain last access time
            domain = self._extract_domain(normalized_url)
            self.domain_last_access[domain] = datetime.now()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status
        
        Returns:
            Queue status dictionary
        """
        # Count URLs by domain
        domain_counts = defaultdict(int)
        for url, info in self.url_queue.items():
            domain_counts[info['domain']] += 1
        
        # Count URLs by depth
        depth_counts = defaultdict(int)
        for url, info in self.url_queue.items():
            depth_counts[info['depth']] += 1
        
        # Count URLs by priority
        priority_counts = defaultdict(int)
        for url, info in self.url_queue.items():
            priority_counts[info['priority']] += 1
        
        return {
            'queue_size': len(self.url_queue),
            'processed_urls': len(self.processed_urls),
            'domains': len(self.domain_queues),
            'domain_distribution': dict(domain_counts),
            'depth_distribution': dict(depth_counts),
            'priority_distribution': dict(priority_counts)
        }
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL with advanced handling
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL or empty string if invalid
        """
        try:
            # Basic validation
            if not url or not isinstance(url, str) or ' ' in url:
                self.logger.warning(f"Invalid URL format: {url}")
                return ''
                
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Parse URL
            parsed = urlparse(url)
            
            # Validate scheme
            if parsed.scheme not in ('http', 'https'):
                self.logger.warning(f"Invalid URL scheme: {url}")
                return ''
            
            # Validate netloc
            if not parsed.netloc:
                self.logger.warning(f"Invalid URL host: {url}")
                return ''
            
            # Convert to lowercase
            netloc = parsed.netloc.lower()
            path = parsed.path
            
            # Remove default ports
            if netloc.endswith(':80') and parsed.scheme == 'http':
                netloc = netloc[:-3]
            elif netloc.endswith(':443') and parsed.scheme == 'https':
                netloc = netloc[:-4]
            
            # Remove duplicate slashes in path
            while '//' in path:
                path = path.replace('//', '/')
            
            # Remove trailing slash from path
            if path.endswith('/') and len(path) > 1:
                path = path[:-1]
            
            # Remove common tracking parameters
            query_params = []
            if parsed.query:
                for param in parsed.query.split('&'):
                    if '=' in param:
                        name, value = param.split('=', 1)
                        # Skip common tracking parameters
                        if name.lower() not in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']:
                            query_params.append(f"{name}={value}")
            
            query = '&'.join(query_params)
            
            # Remove fragment (anchor)
            fragment = ''
            
            # Reconstruct URL
            normalized = urlunparse((parsed.scheme, netloc, path, parsed.params, query, fragment))
            
            return normalized
        except Exception as e:
            self.logger.warning(f"Error normalizing URL {url}: {e}")
            return ''
    
    def _add_to_queue(self, url: str, depth: int, priority: int = 100) -> None:
        """
        Add URL to processing queue with priority
        
        Args:
            url: URL to add
            depth: Depth level
            priority: Priority (lower is higher priority)
        """
        # Extract domain
        domain = self._extract_domain(url)
        
        # Generate URL fingerprint for deduplication
        url_fingerprint = self._generate_url_fingerprint(url)
        
        # Skip if fingerprint already exists
        if url_fingerprint in self.url_fingerprints:
            self.logger.debug(f"Skipping duplicate URL fingerprint: {url}")
            return
        
        # Add fingerprint
        self.url_fingerprints.add(url_fingerprint)
        
        # Add to URL queue
        self.url_queue[url] = {
            'depth': depth,
            'domain': domain,
            'added': datetime.now(),
            'priority': priority,
            'fingerprint': url_fingerprint
        }
        
        # Add to domain queue
        self.domain_queues[domain].append(url)
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL
        
        Args:
            url: URL to extract domain from
            
        Returns:
            Domain name
        """
        try:
            extracted = tldextract.extract(url)
            return f"{extracted.domain}.{extracted.suffix}"
        except Exception:
            # Fallback to simple extraction
            parsed = urlparse(url)
            return parsed.netloc
    
    def _is_excluded(self, url: str) -> bool:
        """
        Check if URL should be excluded based on patterns or domains
        
        Args:
            url: URL to check
            
        Returns:
            True if URL should be excluded, False otherwise
        """
        # Check excluded domains
        domain = self._extract_domain(url)
        if domain in self.excluded_domains:
            return True
        
        # Check excluded patterns
        for pattern in self.excluded_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def _calculate_priority(self, url: str, depth: int) -> int:
        """
        Calculate priority for URL
        
        Args:
            url: URL to calculate priority for
            depth: Depth level
            
        Returns:
            Priority value (lower is higher priority)
        """
        # Base priority is depth (deeper URLs have lower priority)
        priority = depth * 10
        
        # Adjust priority based on domain
        domain = self._extract_domain(url)
        
        # Priority domains get higher priority (lower value)
        if domain in self.priority_domains:
            priority -= 20
        
        # File extensions that might indicate important content
        if re.search(r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$', url, re.IGNORECASE):
            priority -= 5
        
        # URLs with keywords that might indicate important content
        important_keywords = ['about', 'contact', 'product', 'service', 'faq', 'help']
        for keyword in important_keywords:
            if keyword in url.lower():
                priority -= 2
        
        return max(0, priority)  # Ensure priority is not negative
    
    async def _respect_rate_limit(self, domain: str) -> None:
        """
        Respect rate limiting for domain
        
        Args:
            domain: Domain to check rate limit for
        """
        if domain in self.domain_last_access:
            last_access = self.domain_last_access[domain]
            now = datetime.now()
            
            # Calculate time since last access
            elapsed = (now - last_access).total_seconds()
            
            # If not enough time has passed, wait
            if elapsed < self.rate_limit:
                wait_time = self.rate_limit - elapsed
                self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
                await asyncio.sleep(wait_time)
        
        # Update last access time
        self.domain_last_access[domain] = datetime.now()
    
    def _generate_url_fingerprint(self, url: str) -> str:
        """
        Generate fingerprint for URL to detect duplicates
        
        Args:
            url: URL to generate fingerprint for
            
        Returns:
            URL fingerprint
        """
        # Parse URL
        parsed = urlparse(url)
        
        # Create normalized components
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip('/')
        
        # Sort query parameters
        query_parts = []
        if parsed.query:
            for param in sorted(parsed.query.split('&')):
                if '=' in param:
                    name, value = param.split('=', 1)
                    # Skip tracking parameters
                    if name.lower() not in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']:
                        query_parts.append(f"{name}={value}")
        
        query = '&'.join(query_parts)
        
        # Create fingerprint string
        fingerprint_str = f"{scheme}://{netloc}{path}"
        if query:
            fingerprint_str += f"?{query}"
        
        # Hash the fingerprint
        return hashlib.md5(fingerprint_str.encode()).hexdigest()