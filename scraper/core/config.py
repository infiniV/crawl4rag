"""
Configuration Manager for Production Web Scraper

Handles YAML/JSON configuration files and environment variable integration
with validation and mode-specific settings.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CrawlConfig:
    """Configuration for crawl4ai engine"""
    headless: bool = True
    wait_for_images: bool = True
    scan_full_page: bool = True
    scroll_delay: float = 0.5
    accept_downloads: bool = True
    timeout: int = 30


@dataclass
class StorageConfig:
    """Storage configuration for different modes"""
    dev_base_path: str = "./docs"
    dev_files_path: str = "./files"
    prod_rag_api_url: str = "http://217.154.66.145:8000"
    api_key_env: str = "RAG_API_KEY"


@dataclass
class ScraperConfig:
    """Main scraper configuration"""
    mode: str = "dev"
    max_workers: int = 10
    max_depth: int = 3
    rate_limit: float = 1.0
    timeout: int = 30
    default_urls: List[str] = field(default_factory=lambda: [
        "https://pac.com.pk/",
        "https://ztbl.com.pk/",
        "https://ffc.com.pk/kashtkar-desk/",
        "https://aari.punjab.gov.pk/",
        "https://plantprotection.gov.pk/",
        "https://web.uaf.edu.pk/",
        "https://namc.pmd.gov.pk/",
        "https://www.parc.gov.pk/",
        "http://www.amis.pk/",
        "https://agripunjab.gov.pk/",
        "https://www.fao.org/home/en",
        "https://www.pcrwr.gov.pk",
        "https://nwfc.pmd.gov.pk/new/daily-forecast.php",
        "https://www.pmd.gov.pk/en/",
        "https://www.iwmi.org/",
        "https://www.cgiar.org/"
    ])


@dataclass
class LoggingConfig:
    """Logging system configuration"""
    level: str = "INFO"
    file: str = "./logs/scraper.log"
    max_size: str = "100MB"
    backup_count: int = 5


@dataclass
class DomainConfig:
    """RAG domain classification configuration"""
    agriculture: List[str] = field(default_factory=lambda: ["farm", "crop", "soil", "organic", "agriculture"])
    water: List[str] = field(default_factory=lambda: ["irrigation", "water", "drainage", "hydro"])
    weather: List[str] = field(default_factory=lambda: ["weather", "climate", "forecast", "meteorology"])
    crops: List[str] = field(default_factory=lambda: ["crop", "plant", "disease", "pest", "harvest"])
    farm: List[str] = field(default_factory=lambda: ["equipment", "machinery", "operation", "management"])
    marketplace: List[str] = field(default_factory=lambda: ["market", "price", "commodity", "trade"])
    banking: List[str] = field(default_factory=lambda: ["loan", "insurance", "finance", "credit"])
    chat: List[str] = field(default_factory=lambda: ["conversation", "chat", "dialogue", "interaction"])


class ConfigManager:
    """
    Centralized configuration manager with support for YAML/JSON files
    and environment variable integration.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/config.yaml"
        self._config_data: Dict[str, Any] = {}
        self.scraper_config: Optional[ScraperConfig] = None
        self.crawl_config: Optional[CrawlConfig] = None
        self.storage_config: Optional[StorageConfig] = None
        self.logging_config: Optional[LoggingConfig] = None
        self.domain_config: Optional[DomainConfig] = None
        
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file with environment variable override"""
        if config_path:
            self.config_path = config_path
            
        config_file = Path(self.config_path)
        
        # Load default configuration if file doesn't exist
        if not config_file.exists():
            self._config_data = self._get_default_config()
            self._create_default_config_file()
        else:
            # Load from file
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    if config_file.suffix.lower() == '.json':
                        self._config_data = json.load(f)
                    else:  # Assume YAML
                        self._config_data = yaml.safe_load(f) or {}
            except Exception as e:
                raise ConfigurationError(f"Failed to load config from {config_file}: {e}")
        
        # Override with environment variables
        self._apply_env_overrides()
        
        # Parse into dataclass objects
        self._parse_config()
        
        return self._config_data
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration dictionary"""
        return {
            'scraper': {
                'mode': 'dev',
                'max_workers': 10,
                'max_depth': 3,
                'rate_limit': 1.0,
                'timeout': 30
            },
            'crawl4ai': {
                'headless': True,
                'wait_for_images': True,
                'scan_full_page': True,
                'scroll_delay': 0.5,
                'accept_downloads': True,
                'timeout': 30
            },
            'storage': {
                'dev': {
                    'base_path': './docs',
                    'files_path': './files'
                },
                'prod': {
                    'rag_api_url': 'http://217.154.66.145:8000',
                    'api_key_env': 'RAG_API_KEY'
                }
            },
            'domains': {
                'agriculture': ['farm', 'crop', 'soil', 'organic', 'agriculture'],
                'water': ['irrigation', 'water', 'drainage', 'hydro'],
                'weather': ['weather', 'climate', 'forecast', 'meteorology'],
                'crops': ['crop', 'plant', 'disease', 'pest', 'harvest'],
                'farm': ['equipment', 'machinery', 'operation', 'management'],
                'marketplace': ['market', 'price', 'commodity', 'trade'],
                'banking': ['loan', 'insurance', 'finance', 'credit'],
                'chat': ['conversation', 'chat', 'dialogue', 'interaction']
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/scraper.log',
                'max_size': '100MB',
                'backup_count': 5
            }
        }
    
    def _create_default_config_file(self) -> None:
        """Create default configuration file"""
        config_dir = Path(self.config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config_data, f, default_flow_style=False, indent=2)
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        # Mode override
        if os.getenv('SCRAPER_MODE'):
            self._config_data.setdefault('scraper', {})['mode'] = os.getenv('SCRAPER_MODE')
        
        # API key for production
        if os.getenv('RAG_API_KEY'):
            self._config_data.setdefault('storage', {}).setdefault('prod', {})['api_key'] = os.getenv('RAG_API_KEY')
        
        # Worker count override
        if os.getenv('SCRAPER_MAX_WORKERS'):
            try:
                self._config_data.setdefault('scraper', {})['max_workers'] = int(os.getenv('SCRAPER_MAX_WORKERS'))
            except ValueError:
                pass
        
        # Log level override
        if os.getenv('LOG_LEVEL'):
            self._config_data.setdefault('logging', {})['level'] = os.getenv('LOG_LEVEL')
    
    def _parse_config(self) -> None:
        """Parse configuration into dataclass objects"""
        # Scraper config
        scraper_data = self._config_data.get('scraper', {})
        self.scraper_config = ScraperConfig(
            mode=scraper_data.get('mode', 'dev'),
            max_workers=scraper_data.get('max_workers', 10),
            max_depth=scraper_data.get('max_depth', 3),
            rate_limit=scraper_data.get('rate_limit', 1.0),
            timeout=scraper_data.get('timeout', 30)
        )
        
        # Crawl config
        crawl_data = self._config_data.get('crawl4ai', {})
        self.crawl_config = CrawlConfig(
            headless=crawl_data.get('headless', True),
            wait_for_images=crawl_data.get('wait_for_images', True),
            scan_full_page=crawl_data.get('scan_full_page', True),
            scroll_delay=crawl_data.get('scroll_delay', 0.5),
            accept_downloads=crawl_data.get('accept_downloads', True),
            timeout=crawl_data.get('timeout', 30)
        )
        
        # Storage config
        storage_data = self._config_data.get('storage', {})
        dev_storage = storage_data.get('dev', {})
        prod_storage = storage_data.get('prod', {})
        
        self.storage_config = StorageConfig(
            dev_base_path=dev_storage.get('base_path', './docs'),
            dev_files_path=dev_storage.get('files_path', './files'),
            prod_rag_api_url=prod_storage.get('rag_api_url', 'http://217.154.66.145:8000'),
            api_key_env=prod_storage.get('api_key_env', 'RAG_API_KEY')
        )
        
        # Logging config
        logging_data = self._config_data.get('logging', {})
        self.logging_config = LoggingConfig(
            level=logging_data.get('level', 'INFO'),
            file=logging_data.get('file', './logs/scraper.log'),
            max_size=logging_data.get('max_size', '100MB'),
            backup_count=logging_data.get('backup_count', 5)
        )
        
        # Domain config
        domains_data = self._config_data.get('domains', {})
        self.domain_config = DomainConfig(
            agriculture=domains_data.get('agriculture', ['farm', 'crop', 'soil', 'organic', 'agriculture']),
            water=domains_data.get('water', ['irrigation', 'water', 'drainage', 'hydro']),
            weather=domains_data.get('weather', ['weather', 'climate', 'forecast', 'meteorology']),
            crops=domains_data.get('crops', ['crop', 'plant', 'disease', 'pest', 'harvest']),
            farm=domains_data.get('farm', ['equipment', 'machinery', 'operation', 'management']),
            marketplace=domains_data.get('marketplace', ['market', 'price', 'commodity', 'trade']),
            banking=domains_data.get('banking', ['loan', 'insurance', 'finance', 'credit']),
            chat=domains_data.get('chat', ['conversation', 'chat', 'dialogue', 'interaction'])
        )
    
    def validate_config(self, mode: str) -> bool:
        """Validate configuration for specified mode"""
        if not self.scraper_config:
            raise ConfigurationError("Configuration not loaded")
        
        # Validate mode
        if mode not in ['dev', 'prod']:
            raise ConfigurationError(f"Invalid mode: {mode}")
        
        # Production mode validation
        if mode == 'prod':
            api_key = os.getenv(self.storage_config.api_key_env)
            if not api_key:
                raise ConfigurationError(f"API key not found in environment variable: {self.storage_config.api_key_env}")
        
        # Development mode validation
        if mode == 'dev':
            base_path = Path(self.storage_config.dev_base_path)
            files_path = Path(self.storage_config.dev_files_path)
            
            # Create directories if they don't exist
            base_path.mkdir(parents=True, exist_ok=True)
            files_path.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def get_domain_keywords(self) -> Dict[str, List[str]]:
        """Get domain classification keywords"""
        if not self.domain_config:
            raise ConfigurationError("Configuration not loaded")
        
        return {
            'agriculture': self.domain_config.agriculture,
            'water': self.domain_config.water,
            'weather': self.domain_config.weather,
            'crops': self.domain_config.crops,
            'farm': self.domain_config.farm,
            'marketplace': self.domain_config.marketplace,
            'banking': self.domain_config.banking,
            'chat': self.domain_config.chat
        }


class ConfigurationError(Exception):
    """Configuration-related errors"""
    pass