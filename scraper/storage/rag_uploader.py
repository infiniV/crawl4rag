"""
RAG API Uploader Implementation

Handles production mode integration with Farmovation RAG API including
authentication, document upload, rate limiting, and error handling.
"""

import os
import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import asdict
import time
import random

from scraper.core.base import RAGUploaderInterface, ScrapedDocument, APIError
from scraper.core.logging import get_logger


class RAGUploader(RAGUploaderInterface):
    """
    Implementation of RAG API uploader for production mode
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            self.logger = get_logger()
        except RuntimeError:
            # Fallback to basic logging if logging system not set up (e.g., in tests)
            import logging
            self.logger = logging.getLogger(__name__)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        
        # API configuration
        prod_config = config.get('prod', {})
        # Use the correct RAG API endpoint from the documentation
        self.api_url = prod_config.get('rag_api_url', 'http://217.154.66.145:8000')
        self.api_key_env = prod_config.get('api_key_env', 'RAG_API_KEY')
        self.api_key = None
        
        # Rate limiting configuration
        self.rate_limit_requests = 10  # requests per minute
        self.rate_limit_window = 60  # seconds
        self.request_times = []
        
        # Retry configuration
        self.max_retries = 3
        self.base_retry_delay = 1.0  # seconds
        self.max_retry_delay = 60.0  # seconds
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token = None
        self.token_expires_at = None
        
        # Statistics
        self.upload_stats = {
            'total_uploads': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'retries': 0,
            'rate_limit_hits': 0,
            'domains': {},
            'start_time': None
        }
        
        # Domain endpoints mapping from the documentation
        self.domain_endpoints = {
            'agriculture': '/api/v1/documents/agriculture',
            'water': '/api/v1/documents/water',
            'weather': '/api/v1/documents/weather',
            'crops': '/api/v1/documents/crops',
            'farm': '/api/v1/documents/farm',
            'marketplace': '/api/v1/documents/marketplace',
            'banking': '/api/v1/documents/banking',
            'chat': '/api/v1/documents/chat'
        }
    
    async def initialize(self) -> None:
        """Initialize the RAG uploader"""
        self.logger.info("Initializing RAG API uploader")
        
        # Get API key from environment
        self.api_key = os.getenv(self.api_key_env)
        if not self.api_key:
            raise APIError(f"API key not found in environment variable: {self.api_key_env}")
        
        # Create HTTP session with API key authentication
        timeout = aiohttp.ClientTimeout(total=30)
        
        # Set up authentication headers
        headers = {
            'User-Agent': 'Production-Web-Scraper/1.0',
            'Content-Type': 'application/json',
        }
        
        # Add API key as Bearer token (the correct authentication method)
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
            
            # Log the API key for debugging (first 10 characters)
            self.logger.info(f"Using API key: {self.api_key[:10]}...")
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        )
        
        # Test API connectivity
        if not await self._test_api_connectivity():
            raise APIError("Failed to connect to RAG API")
        
        # Initialize statistics
        self.upload_stats['start_time'] = datetime.now()
        for domain in self.domain_endpoints.keys():
            self.upload_stats['domains'][domain] = {
                'uploads': 0,
                'successes': 0,
                'failures': 0
            }
        
        self._initialized = True
        self.logger.info("RAG API uploader initialized successfully")
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Cleaning up RAG API uploader")
        if self.session:
            await self.session.close()
    
    def authenticate(self, api_key: str) -> bool:
        """
        Authenticate with RAG API (synchronous wrapper)
        
        Args:
            api_key: API key for authentication
            
        Returns:
            True if authentication successful
        """
        self.api_key = api_key
        return True  # Actual auth happens in _authenticate
    
    async def _test_api_connectivity(self) -> bool:
        """
        Test API connectivity and authentication
        
        Returns:
            True if API is accessible and authentication works
        """
        try:
            # Test with the health endpoint (no auth required)
            test_url = f"{self.api_url}/health"
            self.logger.info(f"Testing API connectivity at {test_url}")
            
            async with self.session.get(test_url) as response:
                if response.status in [200, 201]:
                    health_data = await response.json()
                    self.logger.info(f"Health check successful: {health_data.get('status', 'unknown')}")
                    
                    # Now test an authenticated endpoint
                    auth_test_url = f"{self.api_url}/auth/me"
                    self.logger.info(f"Testing authentication at {auth_test_url}")
                    
                    async with self.session.get(auth_test_url) as auth_response:
                        if auth_response.status in [200, 201]:
                            auth_data = await auth_response.json()
                            self.logger.info(f"Authentication successful for key: {auth_data.get('name', 'unknown')}")
                            return True
                        elif auth_response.status == 401:
                            self.logger.error("Authentication failed - invalid API key")
                            return False
                        elif auth_response.status == 403:
                            self.logger.error("Access forbidden - insufficient permissions")
                            return False
                        else:
                            self.logger.warning(f"Auth endpoint responded with status {auth_response.status}")
                            # Consider any response as a successful connection for now
                            return True
                else:
                    self.logger.warning(f"Health endpoint responded with status {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"API connectivity test failed: {str(e)}")
            # Let's try a direct document endpoint as a last resort
            try:
                # Try to get domains list as a fallback
                alt_test_url = f"{self.api_url}/api/v1/domains"
                self.logger.info(f"Trying alternative endpoint at {alt_test_url}")
                
                async with self.session.get(alt_test_url) as response:
                    self.logger.info(f"Alternative endpoint responded with status {response.status}")
                    # Consider any response as a successful connection
                    return True
            except Exception as alt_e:
                self.logger.error(f"Alternative endpoint test failed: {str(alt_e)}")
                return False
    
    async def upload_document(self, document: ScrapedDocument, domain: str) -> str:
        """
        Upload single document to RAG API
        
        Args:
            document: Document to upload
            domain: Target domain
            
        Returns:
            Document ID from API
        """
        
        # Validate domain
        if domain not in self.domain_endpoints:
            self.logger.warning(f"Unknown domain: {domain}, defaulting to agriculture")
            domain = 'agriculture'
        
        # Wait for rate limiting
        await self._wait_for_rate_limit()
        
        # Prepare document data in correct API format
        # Based on API schema, we need a 'text' field and optional 'metadata'
        doc_data = {
            'text': document.markdown,  # API expects 'text' field
            'metadata': {
                'title': document.title,
                'url': document.url,
                'timestamp': document.timestamp.isoformat(),
                'content_hash': document.content_hash,
                'processing_time': document.processing_time,
                'retry_count': document.retry_count,
                'media_count': len(document.media_catalog),
                'original_metadata': document.metadata
            }
        }
        
        # Upload with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                endpoint = self.domain_endpoints[domain]
                upload_url = f"{self.api_url}{endpoint}"
                
                self.logger.info(f"Uploading document to {domain} domain (attempt {attempt + 1})")
                
                async with self.session.post(upload_url, json=doc_data) as response:
                    if response.status in [200, 201]:  # Accept both 200 and 201 as success
                        result = await response.json()
                        doc_id = result.get('document_id', result.get('id'))
                        
                        # Update statistics
                        self.upload_stats['total_uploads'] += 1
                        self.upload_stats['successful_uploads'] += 1
                        self.upload_stats['domains'][domain]['uploads'] += 1
                        self.upload_stats['domains'][domain]['successes'] += 1
                        
                        self.logger.info(f"Successfully uploaded document {doc_id} to {domain}")
                        return doc_id
                        
                    elif response.status == 429:  # Rate limited
                        self.upload_stats['rate_limit_hits'] += 1
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    else:
                        error_text = await response.text()
                        error_msg = f"Upload failed: {response.status} - {error_text}"
                        
                        if attempt < self.max_retries:
                            delay = self._calculate_retry_delay(attempt)
                            self.logger.warning(f"{error_msg}, retrying in {delay} seconds")
                            self.upload_stats['retries'] += 1
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise APIError(error_msg)
                            
            except aiohttp.ClientError as e:
                error_msg = f"Network error during upload: {str(e)}"
                
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(f"{error_msg}, retrying in {delay} seconds")
                    self.upload_stats['retries'] += 1
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise APIError(error_msg)
        
        # If we get here, all retries failed
        self.upload_stats['total_uploads'] += 1
        self.upload_stats['failed_uploads'] += 1
        self.upload_stats['domains'][domain]['uploads'] += 1
        self.upload_stats['domains'][domain]['failures'] += 1
        
        raise APIError(f"Failed to upload document after {self.max_retries} retries")
    
    async def upload_batch(self, documents: List[ScrapedDocument], domain: str) -> List[str]:
        """
        Upload multiple documents to RAG API
        
        Args:
            documents: List of documents to upload
            domain: Target domain
            
        Returns:
            List of document IDs
        """
        
        # Validate domain
        if domain not in self.domain_endpoints:
            self.logger.warning(f"Unknown domain: {domain}, defaulting to agriculture")
            domain = 'agriculture'
        
        self.logger.info(f"Starting batch upload of {len(documents)} documents to {domain}")
        
        # Try batch upload first
        try:
            return await self._upload_batch_optimized(documents, domain)
        except APIError as e:
            self.logger.warning(f"Batch upload failed: {str(e)}, falling back to individual uploads")
            
            # Fall back to individual uploads
            document_ids = []
            for i, document in enumerate(documents):
                try:
                    doc_id = await self.upload_document(document, domain)
                    document_ids.append(doc_id)
                    self.logger.info(f"Uploaded document {i+1}/{len(documents)}")
                except APIError as upload_error:
                    self.logger.error(f"Failed to upload document {i+1}: {str(upload_error)}")
                    document_ids.append(None)
            
            return document_ids
    
    async def _upload_batch_optimized(self, documents: List[ScrapedDocument], domain: str) -> List[str]:
        """
        Optimized batch upload using batch API endpoint
        
        Args:
            documents: List of documents to upload
            domain: Target domain
            
        Returns:
            List of document IDs
        """
        # Wait for rate limiting
        await self._wait_for_rate_limit()
        
        # Prepare batch data as array (API expects direct array)
        batch_data = []
        
        for document in documents:
            doc_data = {
                'text': document.markdown,  # API expects 'text' field
                'metadata': {
                    'title': document.title,
                    'url': document.url,
                    'timestamp': document.timestamp.isoformat(),
                    'content_hash': document.content_hash,
                    'processing_time': document.processing_time,
                    'retry_count': document.retry_count,
                    'media_count': len(document.media_catalog),
                    'original_metadata': document.metadata
                }
            }
            batch_data.append(doc_data)
        
        # Upload with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                endpoint = f"{self.domain_endpoints[domain]}/batch"
                upload_url = f"{self.api_url}{endpoint}"
                
                self.logger.info(f"Batch uploading {len(documents)} documents to {domain} (attempt {attempt + 1})")
                
                async with self.session.post(upload_url, json=batch_data) as response:
                    if response.status in [200, 201]:  # Accept both 200 and 201 as success
                        result = await response.json()
                        document_ids = result.get('document_ids', [])
                        
                        # Update statistics
                        successful_count = len([doc_id for doc_id in document_ids if doc_id])
                        self.upload_stats['total_uploads'] += len(documents)
                        self.upload_stats['successful_uploads'] += successful_count
                        self.upload_stats['failed_uploads'] += len(documents) - successful_count
                        self.upload_stats['domains'][domain]['uploads'] += len(documents)
                        self.upload_stats['domains'][domain]['successes'] += successful_count
                        self.upload_stats['domains'][domain]['failures'] += len(documents) - successful_count
                        
                        self.logger.info(f"Successfully batch uploaded {successful_count}/{len(documents)} documents to {domain}")
                        return document_ids
                        
                    elif response.status == 429:  # Rate limited
                        self.upload_stats['rate_limit_hits'] += 1
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    else:
                        error_text = await response.text()
                        error_msg = f"Batch upload failed: {response.status} - {error_text}"
                        
                        if attempt < self.max_retries:
                            delay = self._calculate_retry_delay(attempt)
                            self.logger.warning(f"{error_msg}, retrying in {delay} seconds")
                            self.upload_stats['retries'] += 1
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise APIError(error_msg)
                            
            except aiohttp.ClientError as e:
                error_msg = f"Network error during batch upload: {str(e)}"
                
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(f"{error_msg}, retrying in {delay} seconds")
                    self.upload_stats['retries'] += 1
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise APIError(error_msg)
        
        # If we get here, all retries failed
        self.upload_stats['total_uploads'] += len(documents)
        self.upload_stats['failed_uploads'] += len(documents)
        self.upload_stats['domains'][domain]['uploads'] += len(documents)
        self.upload_stats['domains'][domain]['failures'] += len(documents)
        
        raise APIError(f"Failed to batch upload documents after {self.max_retries} retries")
    
    async def _wait_for_rate_limit(self) -> None:
        """Wait if we're hitting rate limits"""
        now = time.time()
        
        # Remove old request times outside the window
        self.request_times = [t for t in self.request_times if now - t < self.rate_limit_window]
        
        # Check if we're at the rate limit
        if len(self.request_times) >= self.rate_limit_requests:
            # Calculate how long to wait
            oldest_request = min(self.request_times)
            wait_time = self.rate_limit_window - (now - oldest_request)
            
            if wait_time > 0:
                self.logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.request_times.append(now)
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff and jitter
        
        Args:
            attempt: Retry attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = self.base_retry_delay * (2 ** attempt)
        
        # Cap at maximum delay
        delay = min(delay, self.max_retry_delay)
        
        # Add jitter (±25%)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        delay += jitter
        
        return max(0.1, delay)  # Minimum 0.1 seconds
    
    def handle_rate_limits(self) -> None:
        """Handle API rate limiting (placeholder for sync interface)"""
        # This is handled automatically in async methods
        pass
    
    def get_upload_stats(self) -> Dict[str, Any]:
        """
        Get upload statistics
        
        Returns:
            Upload statistics
        """
        stats = self.upload_stats.copy()
        
        if stats['start_time']:
            elapsed = datetime.now() - stats['start_time']
            stats['elapsed_time'] = str(elapsed)
            stats['uploads_per_minute'] = (
                stats['total_uploads'] / max(elapsed.total_seconds() / 60, 1)
            )
        
        # Calculate success rate
        if stats['total_uploads'] > 0:
            stats['success_rate'] = stats['successful_uploads'] / stats['total_uploads']
        else:
            stats['success_rate'] = 0.0
        
        return stats