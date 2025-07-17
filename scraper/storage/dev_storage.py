"""
Development Storage Manager Implementation

Handles local file system storage mimicking RAG structure.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime

from scraper.core.base import StorageManagerInterface, ScrapedDocument
from scraper.core.logging import get_logger


class DevStorageManager(StorageManagerInterface):
    """
    Implementation of development storage manager
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger()
        self.base_path = Path(config.get('dev', {}).get('base_path', './docs'))
        self.files_path = Path(config.get('dev', {}).get('files_path', './files'))
        self.domains = [
            'agriculture', 'water', 'weather', 'crops', 
            'farm', 'marketplace', 'banking', 'chat'
        ]
    
    async def initialize(self) -> None:
        """Initialize the component"""
        self.logger.info("Initializing development storage manager")
        self.create_domain_structure()
        self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Cleaning up development storage manager")
    
    async def save_document(self, document: ScrapedDocument, domain: str) -> str:
        """
        Save document to storage
        
        Args:
            document: Document to save
            domain: Domain to save to
            
        Returns:
            Document ID
        """
        # Ensure domain exists
        if domain not in self.domains:
            self.logger.warning(f"Unknown domain: {domain}, defaulting to agriculture")
            domain = 'agriculture'
        
        # Create domain directory if it doesn't exist
        domain_dir = self.base_path / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename from title
        safe_title = self._create_safe_filename(document.title)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        doc_id = f"{safe_title}_{timestamp}"
        
        # Save markdown content
        md_path = domain_dir / f"{doc_id}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(document.markdown)
        
        # Save metadata
        meta_path = domain_dir / f"{doc_id}.meta.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({
                'url': document.url,
                'title': document.title,
                'timestamp': document.timestamp.isoformat(),
                'content_hash': document.content_hash,
                'domains': document.domain_classifications,
                'metadata': document.metadata
            }, f, indent=2)
        
        self.logger.info(f"Saved document to {md_path}")
        return doc_id
    
    async def save_media_catalog(self, catalog: str, domain: str, source_url: str) -> str:
        """
        Save media catalog
        
        Args:
            catalog: Media catalog content
            domain: Domain to save to
            source_url: Source URL
            
        Returns:
            Catalog ID
        """
        # Ensure domain exists
        if domain not in self.domains:
            self.logger.warning(f"Unknown domain: {domain}, defaulting to agriculture")
            domain = 'agriculture'
        
        # Create domain directory if it doesn't exist
        domain_dir = self.base_path / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename from URL
        safe_url = self._create_safe_filename(source_url)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        catalog_id = f"{safe_url}_media_{timestamp}"
        
        # Save catalog
        catalog_path = domain_dir / f"{catalog_id}.md"
        with open(catalog_path, 'w', encoding='utf-8') as f:
            f.write(catalog)
        
        self.logger.info(f"Saved media catalog to {catalog_path}")
        return catalog_id
    
    def create_domain_structure(self) -> None:
        """Create domain folder structure"""
        self.logger.info("Creating domain folder structure")
        
        # Create base directories
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.files_path.mkdir(parents=True, exist_ok=True)
        
        # Create domain directories
        for domain in self.domains:
            domain_dir = self.base_path / domain
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            files_domain_dir = self.files_path / domain
            files_domain_dir.mkdir(parents=True, exist_ok=True)
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Returns:
            Storage statistics
        """
        stats = {
            'base_path': str(self.base_path),
            'files_path': str(self.files_path),
            'domains': {},
            'total_documents': 0,
            'total_media_catalogs': 0
        }
        
        for domain in self.domains:
            domain_dir = self.base_path / domain
            if domain_dir.exists():
                md_files = list(domain_dir.glob('*.md'))
                meta_files = list(domain_dir.glob('*.meta.json'))
                
                # Count documents and media catalogs
                docs = [f for f in md_files if not f.name.endswith('_media.md')]
                media_catalogs = [f for f in md_files if f.name.endswith('_media.md')]
                
                stats['domains'][domain] = {
                    'documents': len(docs),
                    'media_catalogs': len(media_catalogs),
                    'metadata_files': len(meta_files)
                }
                
                stats['total_documents'] += len(docs)
                stats['total_media_catalogs'] += len(media_catalogs)
        
        return stats
    
    def _create_safe_filename(self, text: str) -> str:
        """Create safe filename from text"""
        # Replace invalid characters
        safe = "".join(c if c.isalnum() else "_" for c in text)
        # Limit length
        safe = safe[:50]
        # Ensure not empty
        if not safe:
            safe = "document"
        return safe