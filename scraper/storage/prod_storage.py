"""
Production Storage Manager Implementation

Handles production mode storage using RAG API integration.
"""

from typing import Dict, Any, List
from datetime import datetime

from scraper.core.base import StorageManagerInterface, ScrapedDocument
from scraper.core.logging import get_logger
from scraper.storage.rag_uploader import RAGUploader


class ProdStorageManager(StorageManagerInterface):
    """
    Implementation of production storage manager using RAG API
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
        self.rag_uploader = RAGUploader(config.get('storage', {}))
        self.domains = [
            'agriculture', 'water', 'weather', 'crops', 
            'farm', 'marketplace', 'banking', 'chat'
        ]
        
        # Track uploaded documents
        self.uploaded_documents = {}  # domain -> list of doc_ids
        for domain in self.domains:
            self.uploaded_documents[domain] = []
    
    async def initialize(self) -> None:
        """Initialize the component"""
        self.logger.info("Initializing production storage manager")
        await self.rag_uploader.initialize()
        self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Cleaning up production storage manager")
        await self.rag_uploader.cleanup()
    
    async def save_document(self, document: ScrapedDocument, domain: str) -> str:
        """
        Save document to RAG API
        
        Args:
            document: Document to save
            domain: Domain to save to
            
        Returns:
            Document ID from RAG API
        """
        # Ensure domain exists
        if domain not in self.domains:
            self.logger.warning(f"Unknown domain: {domain}, defaulting to agriculture")
            domain = 'agriculture'
        
        try:
            # Upload document to RAG API
            doc_id = await self.rag_uploader.upload_document(document, domain)
            
            # Track the uploaded document
            self.uploaded_documents[domain].append({
                'doc_id': doc_id,
                'url': document.url,
                'title': document.title,
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.info(f"Successfully saved document {doc_id} to {domain} domain")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Failed to save document to {domain}: {str(e)}")
            raise
    
    async def save_media_catalog(self, catalog: str, domain: str, source_url: str) -> str:
        """
        Save media catalog as a document to RAG API
        
        Args:
            catalog: Media catalog content
            domain: Domain to save to
            source_url: Source URL
            
        Returns:
            Document ID from RAG API
        """
        # Ensure domain exists
        if domain not in self.domains:
            self.logger.warning(f"Unknown domain: {domain}, defaulting to agriculture")
            domain = 'agriculture'
        
        try:
            # Create a document for the media catalog
            catalog_document = ScrapedDocument(
                url=source_url,
                title=f"Media Catalog - {source_url}",
                content=catalog,
                markdown=catalog,
                metadata={'type': 'media_catalog', 'source_url': source_url},
                media_catalog=[],
                domain_classifications=[domain],
                timestamp=datetime.now(),
                content_hash=f"media_catalog_{hash(catalog)}",
                processing_time=0.0,
                retry_count=0
            )
            
            # Upload catalog as document
            doc_id = await self.rag_uploader.upload_document(catalog_document, domain)
            
            # Track the uploaded catalog
            self.uploaded_documents[domain].append({
                'doc_id': doc_id,
                'url': source_url,
                'title': catalog_document.title,
                'timestamp': datetime.now().isoformat(),
                'type': 'media_catalog'
            })
            
            self.logger.info(f"Successfully saved media catalog {doc_id} to {domain} domain")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Failed to save media catalog to {domain}: {str(e)}")
            raise
    
    def create_domain_structure(self) -> None:
        """Create domain structure (not applicable for production mode)"""
        self.logger.info("Domain structure managed by RAG API")
        # Initialize tracking for all domains
        for domain in self.domains:
            if domain not in self.uploaded_documents:
                self.uploaded_documents[domain] = []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Returns:
            Storage statistics
        """
        # Get RAG uploader stats
        rag_stats = self.rag_uploader.get_upload_stats()
        
        # Combine with our tracking stats
        stats = {
            'mode': 'production',
            'rag_api_url': self.rag_uploader.api_url,
            'domains': {},
            'total_documents': 0,
            'total_media_catalogs': 0,
            'rag_uploader_stats': rag_stats
        }
        
        for domain in self.domains:
            domain_docs = self.uploaded_documents.get(domain, [])
            regular_docs = [d for d in domain_docs if d.get('type') != 'media_catalog']
            media_catalogs = [d for d in domain_docs if d.get('type') == 'media_catalog']
            
            stats['domains'][domain] = {
                'documents': len(regular_docs),
                'media_catalogs': len(media_catalogs),
                'total': len(domain_docs),
                'recent_uploads': domain_docs[-5:] if domain_docs else []  # Last 5 uploads
            }
            
            stats['total_documents'] += len(regular_docs)
            stats['total_media_catalogs'] += len(media_catalogs)
        
        return stats
    
    async def upload_batch_to_domain(self, documents: List[ScrapedDocument], domain: str) -> List[str]:
        """
        Upload multiple documents to a specific domain
        
        Args:
            documents: List of documents to upload
            domain: Target domain
            
        Returns:
            List of document IDs
        """
        # Ensure domain exists
        if domain not in self.domains:
            self.logger.warning(f"Unknown domain: {domain}, defaulting to agriculture")
            domain = 'agriculture'
        
        try:
            # Upload batch to RAG API
            doc_ids = await self.rag_uploader.upload_batch(documents, domain)
            
            # Track the uploaded documents
            for i, doc_id in enumerate(doc_ids):
                if doc_id:  # Only track successful uploads
                    self.uploaded_documents[domain].append({
                        'doc_id': doc_id,
                        'url': documents[i].url,
                        'title': documents[i].title,
                        'timestamp': datetime.now().isoformat()
                    })
            
            successful_count = len([doc_id for doc_id in doc_ids if doc_id])
            self.logger.info(f"Successfully uploaded {successful_count}/{len(documents)} documents to {domain} domain")
            return doc_ids
            
        except Exception as e:
            self.logger.error(f"Failed to upload batch to {domain}: {str(e)}")
            raise
    
    async def upload_multi_domain(self, document: ScrapedDocument, domains: List[str]) -> Dict[str, str]:
        """
        Upload document to multiple domains
        
        Args:
            document: Document to upload
            domains: List of target domains
            
        Returns:
            Dictionary mapping domain to document ID
        """
        results = {}
        
        for domain in domains:
            try:
                doc_id = await self.save_document(document, domain)
                results[domain] = doc_id
                self.logger.info(f"Successfully uploaded to {domain}: {doc_id}")
            except Exception as e:
                self.logger.error(f"Failed to upload to {domain}: {str(e)}")
                results[domain] = None
        
        return results
    
    def get_domain_document_count(self, domain: str) -> int:
        """
        Get document count for a specific domain
        
        Args:
            domain: Domain name
            
        Returns:
            Number of documents in domain
        """
        return len(self.uploaded_documents.get(domain, []))
    
    def get_recent_uploads(self, domain: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent uploads for a domain
        
        Args:
            domain: Domain name
            limit: Maximum number of uploads to return
            
        Returns:
            List of recent upload information
        """
        domain_docs = self.uploaded_documents.get(domain, [])
        return domain_docs[-limit:] if domain_docs else []