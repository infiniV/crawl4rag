"""
Scraper Orchestrator Implementation

Main orchestrator for the scraping process that coordinates all components.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from scraper.core.base import (
    ScraperOrchestrator, 
    ProcessingMode, 
    ProcessingResult,
    ProcessingStatus,
    URLManagerInterface,
    CrawlEngineInterface,
    ContentProcessorInterface,
    MediaExtractorInterface,
    ContentClassifierInterface,
    StorageManagerInterface,
    RAGUploaderInterface,
    ProgressMonitorInterface
)
from scraper.core.logging import get_logger


class ScraperOrchestratorImpl(ScraperOrchestrator):
    """
    Implementation of the scraper orchestrator
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger()
    
    async def initialize(self) -> None:
        """Initialize all components"""
        self.logger.info("Initializing scraper orchestrator")
        
        # Initialize all registered components
        components = [
            self.url_manager,
            self.crawl_engine,
            self.content_processor,
            self.media_extractor,
            self.content_classifier,
            self.storage_manager,
            self.rag_uploader,
            self.progress_monitor
        ]
        
        for component in components:
            if component:
                await component.initialize()
        
        self._initialized = True
        self.logger.info("Scraper orchestrator initialized")
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Cleaning up scraper orchestrator")
        
        # Clean up all registered components
        components = [
            self.url_manager,
            self.crawl_engine,
            self.content_processor,
            self.media_extractor,
            self.content_classifier,
            self.storage_manager,
            self.rag_uploader,
            self.progress_monitor
        ]
        
        for component in components:
            if component:
                await component.cleanup()
        
        self.logger.info("Scraper orchestrator cleanup completed")
    
    async def process_urls(self, urls: List[str], mode: ProcessingMode) -> List[ProcessingResult]:
        """
        Process list of URLs
        
        Args:
            urls: List of URLs to process
            mode: Processing mode (development or production)
            
        Returns:
            List of processing results
        """
        if not self._initialized:
            await self.initialize()
        
        self.logger.info(f"Processing {len(urls)} URLs in {mode.value} mode")
        
        # Validate URLs
        if self.url_manager:
            valid_urls = self.url_manager.validate_urls(urls)
            self.logger.info(f"Validated {len(valid_urls)}/{len(urls)} URLs")
        else:
            valid_urls = urls
        
        # Start progress monitoring
        if self.progress_monitor:
            self.progress_monitor.start_monitoring(len(valid_urls))
        
        # Process URLs
        results = []
        total_pages_processed = 0
        
        for i, url in enumerate(valid_urls):
            try:
                result = await self.process_single_url(url, mode)
                results.append(result)
                
                # Update progress with the total pages processed
                if self.progress_monitor:
                    self.progress_monitor.update_progress(
                        i + 1,  # Just update with the current URL index
                        f"Processed {url} - {'Success' if result.success else 'Failed'}"
                    )
            except Exception as e:
                self.logger.error(f"Error processing URL {url}: {e}", exc_info=True)
                results.append(ProcessingResult(
                    url=url,
                    success=False,
                    error_message=str(e),
                    status=ProcessingStatus.FAILED
                ))
        
        # Generate report
        if self.progress_monitor:
            report = self.progress_monitor.generate_report()
            self.logger.info(f"Processing report:\n{report}")
        
        return results
    
    async def process_single_url(self, url: str, mode: ProcessingMode) -> ProcessingResult:
        """
        Process a single URL
        
        Args:
            url: URL to process
            mode: Processing mode (development or production)
            
        Returns:
            Processing result
        """
        start_time = time.time()
        result = ProcessingResult(
            url=url,
            success=False,
            status=ProcessingStatus.IN_PROGRESS
        )
        
        try:
            self.logger.info(f"Processing URL: {url}")
            
            # Crawl the URL
            if not self.crawl_engine:
                raise ValueError("Crawl engine not initialized")
            
            # Check if deep crawling is enabled in config
            scraper_config = self.config.get('scraper', {})
            max_depth = scraper_config.get('max_depth', 0)
            
            # Enable deep crawling if max_depth > 1
            deep_crawl = max_depth > 1
            if deep_crawl:
                self.logger.info(f"Using deep crawling with max depth {max_depth} for {url}")
                
            crawl_result = await self.crawl_engine.crawl_url(url, {
                'deep_crawl': deep_crawl,
                'url': url
            })
            
            # Store the crawl result in the processing result for later reference
            result.crawl_result = crawl_result
            
            # Update progress monitor with actual pages crawled for deep crawling
            if deep_crawl and self.progress_monitor and hasattr(crawl_result, 'pages_crawled') and crawl_result.pages_crawled > 1:
                # Update the total URLs to include deep crawled pages
                additional_pages = crawl_result.pages_crawled - 1  # Subtract 1 because the main URL is already counted
                self.progress_monitor.add_deep_crawled_pages(additional_pages)
                self.logger.info(f"Added {additional_pages} deep crawled pages to progress monitoring")
            
            if not crawl_result.success:
                result.error_message = crawl_result.error_message
                result.status = ProcessingStatus.FAILED
                return result
            
            # Process content
            if not self.content_processor:
                raise ValueError("Content processor not initialized")
            
            # Process discovered URLs
            if self.url_manager and crawl_result.links:
                self.url_manager.add_discovered_urls(crawl_result.links, 1)
            
            # Extract media
            media_items = {}
            if self.media_extractor:
                media_items = self.media_extractor.extract_media_urls(crawl_result)
            
            # Classify content
            domains = ["agriculture"]  # Default domain
            if self.content_classifier:
                metadata = self.content_processor.extract_metadata(crawl_result)
                domains = self.content_classifier.classify_content(crawl_result.markdown, metadata)
            
            # Create document
            document = self.content_processor.create_document(
                crawl_result, 
                domains,
                media_items
            )
            
            # Store document based on mode
            if mode == ProcessingMode.DEVELOPMENT:
                if not self.storage_manager:
                    raise ValueError("Storage manager not initialized")
                
                for domain in domains:
                    doc_id = await self.storage_manager.save_document(document, domain)
                    self.logger.info(f"Saved document to {domain} domain with ID: {doc_id}")
                    
                    # Save media catalog
                    if media_items:
                        catalog = self.media_extractor.create_media_catalog(media_items)
                        catalog_id = await self.storage_manager.save_media_catalog(
                            catalog, domain, url
                        )
                        self.logger.info(f"Saved media catalog to {domain} domain with ID: {catalog_id}")
            else:
                # Production mode - try to use RAG uploader if available
                if not self.rag_uploader:
                    self.logger.warning("RAG uploader not initialized, falling back to local storage")
                    
                    # Fall back to local storage
                    if not self.storage_manager:
                        raise ValueError("Storage manager not initialized")
                    
                    for domain in domains:
                        doc_id = await self.storage_manager.save_document(document, domain)
                        self.logger.info(f"Saved document to {domain} domain with ID: {doc_id}")
                        
                        # Save media catalog
                        if media_items:
                            catalog = self.media_extractor.create_media_catalog(media_items)
                            catalog_id = await self.storage_manager.save_media_catalog(
                                catalog, domain, url
                            )
                            self.logger.info(f"Saved media catalog to {domain} domain with ID: {catalog_id}")
                else:
                    # Use RAG uploader
                    for domain in domains:
                        try:
                            doc_id = await self.rag_uploader.upload_document(document, domain)
                            self.logger.info(f"Uploaded document to {domain} domain with ID: {doc_id}")
                        except Exception as e:
                            self.logger.error(f"Failed to upload to RAG API: {str(e)}, falling back to local storage")
                            
                            # Fall back to local storage
                            if self.storage_manager:
                                doc_id = await self.storage_manager.save_document(document, domain)
                                self.logger.info(f"Saved document to {domain} domain with ID: {doc_id}")
                                
                                # Save media catalog
                                if media_items:
                                    catalog = self.media_extractor.create_media_catalog(media_items)
                                    catalog_id = await self.storage_manager.save_media_catalog(
                                        catalog, domain, url
                                    )
                                    self.logger.info(f"Saved media catalog to {domain} domain with ID: {catalog_id}")
                            else:
                                raise ValueError("Storage manager not initialized for fallback")
            
            # Mark as successful
            result.success = True
            result.document = document
            result.status = ProcessingStatus.COMPLETED
            
        except Exception as e:
            self.logger.error(f"Error processing URL {url}: {e}", exc_info=True)
            result.error_message = str(e)
            result.status = ProcessingStatus.FAILED
        
        # Update processing time
        result.processing_time = time.time() - start_time
        
        return result