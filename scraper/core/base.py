"""
Base Classes and Interfaces for Production Web Scraper

Defines abstract base classes and interfaces for all major components
to ensure consistent architecture and enable extensibility.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ProcessingMode(Enum):
    """Processing modes for the scraper"""
    DEVELOPMENT = "dev"
    PRODUCTION = "prod"


class ProcessingStatus(Enum):
    """Status of processing operations"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ScrapedDocument:
    """Data model for scraped document"""
    url: str
    title: str
    content: str
    markdown: str
    metadata: Dict[str, Any]
    media_catalog: List[Dict[str, Any]]
    domain_classifications: List[str]
    timestamp: datetime
    content_hash: str
    processing_time: float = 0.0
    retry_count: int = 0


@dataclass
class MediaItem:
    """Data model for media items"""
    url: str
    type: str  # image, pdf, doc, etc.
    alt_text: Optional[str] = None
    file_size: Optional[int] = None
    local_path: Optional[str] = None
    download_status: str = "pending"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProcessingResult:
    """Result of processing a single URL"""
    url: str
    success: bool
    document: Optional[ScrapedDocument] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    retry_count: int = 0
    status: ProcessingStatus = ProcessingStatus.NOT_STARTED


@dataclass
class CrawlResult:
    """Result from crawl4ai engine"""
    url: str
    html: str
    markdown: str
    links: List[str]
    media: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class BaseComponent(ABC):
    """Base class for all scraper components"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the component"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources"""
        pass
    
    def is_initialized(self) -> bool:
        """Check if component is initialized"""
        return self._initialized


class URLManagerInterface(BaseComponent):
    """Interface for URL management and validation"""
    
    @abstractmethod
    def validate_urls(self, urls: List[str]) -> List[str]:
        """Validate and filter URLs"""
        pass
    
    @abstractmethod
    def add_discovered_urls(self, urls: List[str], depth: int) -> None:
        """Add newly discovered URLs to processing queue"""
        pass
    
    @abstractmethod
    def get_next_batch(self, batch_size: int) -> List[str]:
        """Get next batch of URLs to process"""
        pass
    
    @abstractmethod
    def mark_processed(self, url: str, success: bool) -> None:
        """Mark URL as processed"""
        pass
    
    @abstractmethod
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status"""
        pass


class CrawlEngineInterface(BaseComponent):
    """Interface for web crawling engine"""
    
    @abstractmethod
    async def crawl_url(self, url: str, config: Dict[str, Any]) -> CrawlResult:
        """Crawl a single URL"""
        pass
    
    @abstractmethod
    async def crawl_batch(self, urls: List[str], config: Dict[str, Any]) -> List[CrawlResult]:
        """Crawl multiple URLs concurrently"""
        pass
    
    @abstractmethod
    def get_browser_config(self) -> Dict[str, Any]:
        """Get browser configuration"""
        pass


class ContentProcessorInterface(BaseComponent):
    """Interface for content processing"""
    
    @abstractmethod
    def convert_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown"""
        pass
    
    @abstractmethod
    def extract_metadata(self, result: CrawlResult) -> Dict[str, Any]:
        """Extract metadata from crawl result"""
        pass
    
    @abstractmethod
    def validate_content_quality(self, content: str) -> bool:
        """Validate content quality"""
        pass
    
    @abstractmethod
    def detect_duplicates(self, content: str) -> bool:
        """Detect duplicate content"""
        pass
    
    @abstractmethod
    def calculate_content_hash(self, content: str) -> str:
        """Calculate content hash for deduplication"""
        pass


class MediaExtractorInterface(BaseComponent):
    """Interface for media extraction and management"""
    
    @abstractmethod
    def extract_media_urls(self, result: CrawlResult) -> Dict[str, List[MediaItem]]:
        """Extract media URLs from crawl result"""
        pass
    
    @abstractmethod
    def create_media_catalog(self, media_data: Dict[str, List[MediaItem]]) -> str:
        """Create media catalog in markdown format"""
        pass
    
    @abstractmethod
    async def download_files(self, media_items: List[MediaItem], destination: str) -> List[str]:
        """Download media files"""
        pass
    
    @abstractmethod
    def organize_files(self, files: List[str], source_domain: str) -> None:
        """Organize downloaded files by domain and type"""
        pass


class ContentClassifierInterface(BaseComponent):
    """Interface for content classification"""
    
    @abstractmethod
    def classify_content(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """Classify content into RAG domains"""
        pass
    
    @abstractmethod
    def get_domain_keywords(self) -> Dict[str, List[str]]:
        """Get domain classification keywords"""
        pass
    
    @abstractmethod
    def calculate_relevance_score(self, content: str, domain: str) -> float:
        """Calculate relevance score for a domain"""
        pass


class StorageManagerInterface(BaseComponent):
    """Interface for storage management"""
    
    @abstractmethod
    async def save_document(self, document: ScrapedDocument, domain: str) -> str:
        """Save document to storage"""
        pass
    
    @abstractmethod
    async def save_media_catalog(self, catalog: str, domain: str, source_url: str) -> str:
        """Save media catalog"""
        pass
    
    @abstractmethod
    def create_domain_structure(self) -> None:
        """Create domain folder structure"""
        pass
    
    @abstractmethod
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        pass


class RAGUploaderInterface(BaseComponent):
    """Interface for RAG API integration"""
    
    @abstractmethod
    def authenticate(self, api_key: str) -> bool:
        """Authenticate with RAG API"""
        pass
    
    @abstractmethod
    async def upload_document(self, document: ScrapedDocument, domain: str) -> str:
        """Upload document to RAG API"""
        pass
    
    @abstractmethod
    async def upload_batch(self, documents: List[ScrapedDocument], domain: str) -> List[str]:
        """Upload multiple documents"""
        pass
    
    @abstractmethod
    def handle_rate_limits(self) -> None:
        """Handle API rate limiting"""
        pass
    
    @abstractmethod
    def get_upload_stats(self) -> Dict[str, Any]:
        """Get upload statistics"""
        pass


class ProgressMonitorInterface(BaseComponent):
    """Interface for progress monitoring"""
    
    @abstractmethod
    def start_monitoring(self, total_urls: int) -> None:
        """Start progress monitoring"""
        pass
    
    @abstractmethod
    def update_progress(self, completed: int, message: str = "") -> None:
        """Update progress"""
        pass
    
    @abstractmethod
    def add_error(self, error: str, context: Dict[str, Any] = None) -> None:
        """Add error to monitoring"""
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics"""
        pass
    
    @abstractmethod
    def generate_report(self) -> str:
        """Generate progress report"""
        pass


class ScraperOrchestrator(BaseComponent):
    """Main orchestrator for the scraping process"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url_manager: Optional[URLManagerInterface] = None
        self.crawl_engine: Optional[CrawlEngineInterface] = None
        self.content_processor: Optional[ContentProcessorInterface] = None
        self.media_extractor: Optional[MediaExtractorInterface] = None
        self.content_classifier: Optional[ContentClassifierInterface] = None
        self.storage_manager: Optional[StorageManagerInterface] = None
        self.rag_uploader: Optional[RAGUploaderInterface] = None
        self.progress_monitor: Optional[ProgressMonitorInterface] = None
    
    @abstractmethod
    async def process_urls(self, urls: List[str], mode: ProcessingMode) -> List[ProcessingResult]:
        """Process list of URLs"""
        pass
    
    @abstractmethod
    async def process_single_url(self, url: str, mode: ProcessingMode) -> ProcessingResult:
        """Process a single URL"""
        pass
    
    def register_component(self, component_type: str, component: BaseComponent) -> None:
        """Register a component with the orchestrator"""
        if component_type == "url_manager":
            self.url_manager = component
        elif component_type == "crawl_engine":
            self.crawl_engine = component
        elif component_type == "content_processor":
            self.content_processor = component
        elif component_type == "media_extractor":
            self.media_extractor = component
        elif component_type == "content_classifier":
            self.content_classifier = component
        elif component_type == "storage_manager":
            self.storage_manager = component
        elif component_type == "rag_uploader":
            self.rag_uploader = component
        elif component_type == "progress_monitor":
            self.progress_monitor = component
        else:
            raise ValueError(f"Unknown component type: {component_type}")


class ScraperError(Exception):
    """Base exception for scraper errors"""
    pass


class ConfigurationError(ScraperError):
    """Configuration-related errors"""
    pass


class CrawlingError(ScraperError):
    """Crawling-related errors"""
    pass


class ProcessingError(ScraperError):
    """Content processing errors"""
    pass


class StorageError(ScraperError):
    """Storage-related errors"""
    pass


class APIError(ScraperError):
    """API-related errors"""
    pass