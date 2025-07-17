"""
Component Factory for Production Web Scraper

This module provides functions to create and register components with the orchestrator.
"""

from typing import Dict, Any, List
import time

from scraper.core.base import ScraperOrchestrator, BaseComponent
from scraper.core.logging import get_logger
from scraper.core.url_manager import URLManager
from scraper.core.crawl_engine import CrawlEngine
from scraper.processors.content import ContentProcessor
from scraper.processors.media import MediaExtractor
from scraper.processors.classifier import ContentClassifier
from scraper.storage.dev_storage import DevStorageManager
from scraper.storage.prod_storage import ProdStorageManager
from scraper.storage.rag_uploader import RAGUploader
from scraper.core.logging import LoggingManager


def create_and_register_components(orchestrator: ScraperOrchestrator, config: Dict[str, Any]) -> None:
    """
    Create and register all components with the orchestrator.
    
    Args:
        orchestrator: The orchestrator to register components with
        config: Configuration dictionary
    """
    # Create URL manager
    url_manager = URLManager(config)
    orchestrator.register_component("url_manager", url_manager)
    
    # Create crawl engine
    crawl_engine = CrawlEngine(config)
    orchestrator.register_component("crawl_engine", crawl_engine)
    
    # Create content processor
    content_processor = ContentProcessor(config)
    orchestrator.register_component("content_processor", content_processor)
    
    # Create media extractor
    media_extractor = MediaExtractor(config)
    orchestrator.register_component("media_extractor", media_extractor)
    
    # Create content classifier wrapper
    class ContentClassifierWrapper(BaseComponent):
        def __init__(self, config: Dict[str, Any]):
            super().__init__(config)
            domain_keywords = config.get('domains', {})
            self.classifier = ContentClassifier(
                domain_keywords=domain_keywords,
                default_domain='agriculture',
                min_confidence_threshold=0.1
            )
            
        async def initialize(self) -> None:
            # ContentClassifier doesn't need initialization
            self._initialized = True
            
        async def cleanup(self) -> None:
            # ContentClassifier doesn't need cleanup
            pass
            
        def classify_content(self, content: str, metadata: Dict[str, Any]) -> List[str]:
            result = self.classifier.classify_content(content, metadata)
            return result.all_domains
            
        def get_domain_keywords(self) -> Dict[str, List[str]]:
            return self.classifier.get_domain_keywords()
            
        def calculate_relevance_score(self, content: str, domain: str) -> float:
            return self.classifier.calculate_relevance_score(content, domain)
    
    # Create and register the wrapper
    content_classifier = ContentClassifierWrapper(config)
    orchestrator.register_component("content_classifier", content_classifier)
    
    # Create storage manager based on mode
    mode = config.get('scraper', {}).get('mode', 'dev')
    if mode.lower() == 'dev':
        storage_manager = DevStorageManager(config)
    else:
        storage_manager = ProdStorageManager(config)
    orchestrator.register_component("storage_manager", storage_manager)
    
    # Create RAG uploader only for production mode
    print(f"Component factory mode: {mode}")
    if mode.lower() == 'prod':
        print("Creating RAG uploader for production mode")
        rag_uploader = RAGUploader(config)
        orchestrator.register_component("rag_uploader", rag_uploader)
    else:
        print("Skipping RAG uploader creation for non-production mode")
    
    # Create progress monitor wrapper
    class ProgressMonitorWrapper(BaseComponent):
        def __init__(self, config: Dict[str, Any]):
            super().__init__(config)
            self.logger = get_logger()
            self.total_urls = 0
            self.completed_urls = 0
            self.errors = []
            self.start_time = None
            
        async def initialize(self) -> None:
            self._initialized = True
            
        async def cleanup(self) -> None:
            pass
            
        def start_monitoring(self, total_urls: int) -> None:
            self.total_urls = total_urls
            self.completed_urls = 0
            self.errors = []
            self.start_time = time.time()
            self.logger.info(f"Starting to process {total_urls} URLs")
            
        def update_progress(self, completed: int, message: str = "") -> None:
            self.completed_urls = completed
            percent = (completed / max(self.total_urls, 1)) * 100
            self.logger.info(f"Progress: {completed}/{self.total_urls} ({percent:.1f}%) - {message}")
            
        def add_error(self, error: str, context: Dict[str, Any] = None) -> None:
            self.errors.append((error, context or {}))
            self.logger.error(f"Error: {error} - Context: {context}")
            
        def get_statistics(self) -> Dict[str, Any]:
            elapsed = time.time() - (self.start_time or time.time())
            return {
                'total_urls': self.total_urls,
                'completed_urls': self.completed_urls,
                'error_count': len(self.errors),
                'elapsed_time': elapsed,
                'urls_per_second': self.completed_urls / max(elapsed, 1)
            }
            
        def generate_report(self) -> str:
            stats = self.get_statistics()
            report = [
                f"Processing Report:",
                f"- Total URLs: {stats['total_urls']}",
                f"- Completed: {stats['completed_urls']} ({(stats['completed_urls'] / max(stats['total_urls'], 1)) * 100:.1f}%)",
                f"- Errors: {stats['error_count']}",
                f"- Elapsed Time: {stats['elapsed_time']:.2f} seconds",
                f"- Processing Rate: {stats['urls_per_second']:.2f} URLs/second"
            ]
            return "\n".join(report)
    
    # Create and register the wrapper
    progress_monitor = ProgressMonitorWrapper(config)
    orchestrator.register_component("progress_monitor", progress_monitor)