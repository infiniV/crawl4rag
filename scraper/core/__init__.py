"""
Core components for Production Web Scraper

This package contains the core components for the scraper including:
- Base classes and interfaces
- Configuration management
- Logging system
- Orchestrator implementation
"""

from scraper.core.base import (
    ProcessingMode,
    ProcessingStatus,
    ScrapedDocument,
    MediaItem,
    ProcessingResult,
    CrawlResult,
    BaseComponent,
    URLManagerInterface,
    CrawlEngineInterface,
    ContentProcessorInterface,
    MediaExtractorInterface,
    ContentClassifierInterface,
    StorageManagerInterface,
    RAGUploaderInterface,
    ProgressMonitorInterface,
    ScraperOrchestrator,
    ScraperError,
    ConfigurationError,
    CrawlingError,
    ProcessingError,
    StorageError,
    APIError
)

from scraper.core.config import (
    ConfigManager,
    CrawlConfig,
    StorageConfig,
    ScraperConfig,
    LoggingConfig,
    DomainConfig,
    ConfigurationError
)

from scraper.core.logging import (
    LoggingManager,
    get_logger,
    setup_logging
)

from scraper.core.orchestrator import (
    ScraperOrchestratorImpl
)

from scraper.core.url_manager import (
    URLManager,
    URLPriority,
    URLStatus,
    URLInfo,
    DomainRateLimit,
    URLValidationError
)

from scraper.core.crawl_engine import (
    CrawlEngine,
    SessionInfo
)

__all__ = [
    # Base classes
    'ProcessingMode',
    'ProcessingStatus',
    'ScrapedDocument',
    'MediaItem',
    'ProcessingResult',
    'CrawlResult',
    'BaseComponent',
    'URLManagerInterface',
    'CrawlEngineInterface',
    'ContentProcessorInterface',
    'MediaExtractorInterface',
    'ContentClassifierInterface',
    'StorageManagerInterface',
    'RAGUploaderInterface',
    'ProgressMonitorInterface',
    'ScraperOrchestrator',
    'ScraperError',
    'ConfigurationError',
    'CrawlingError',
    'ProcessingError',
    'StorageError',
    'APIError',
    
    # Configuration
    'ConfigManager',
    'CrawlConfig',
    'StorageConfig',
    'ScraperConfig',
    'LoggingConfig',
    'DomainConfig',
    
    # Logging
    'LoggingManager',
    'get_logger',
    'setup_logging',
    
    # Orchestrator
    'ScraperOrchestratorImpl',
    
    # URL Management
    'URLManager',
    'URLPriority',
    'URLStatus',
    'URLInfo',
    'DomainRateLimit',
    'URLValidationError',
    
    # Crawl Engine
    'CrawlEngine',
    'SessionInfo'
]