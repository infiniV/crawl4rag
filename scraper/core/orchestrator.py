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
        for i, url in enumerate(valid_urls):
            try:
                result = await self.process_single_url(url, mode)
                results.append(result)
                
                # Update progress
                if self.progress_monitor:
                    self.progress_monitor.update_progress(
                        i + 1, 
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
            
            crawl_result = await self.crawl_engine.crawl_url(url, {})
            
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
                if not self.rag_uploader:
                    raise ValueError("RAG uploader not initialized")
                
                for domain in domains:
                    doc_id = await self.rag_uploader.upload_document(document, domain)
                    self.logger.info(f"Uploaded document to {domain} domain with ID: {doc_id}")
            
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