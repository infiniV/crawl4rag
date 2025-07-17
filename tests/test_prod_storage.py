"""
Tests for Production Storage Manager

Tests production mode storage functionality including RAG API integration,
multi-domain uploads, and batch operations.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from scraper.storage.prod_storage import ProdStorageManager
from scraper.core.base import ScrapedDocument


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        'storage': {
            'prod': {
                'rag_api_url': 'http://test-api.example.com',
                'api_key_env': 'TEST_RAG_API_KEY'
            }
        }
    }


@pytest.fixture
def sample_document():
    """Sample scraped document for testing"""
    return ScrapedDocument(
        url='https://example.com/test',
        title='Test Document',
        content='This is test content',
        markdown='# Test Document\n\nThis is test content',
        metadata={'source': 'test'},
        media_catalog=[],
        domain_classifications=['agriculture'],
        timestamp=datetime.now(),
        content_hash='test_hash_123',
        processing_time=1.5,
        retry_count=0
    )


@pytest.fixture
def mock_rag_uploader():
    """Mock RAG uploader"""
    uploader = AsyncMock()
    uploader.initialize = AsyncMock()
    uploader.cleanup = AsyncMock()
    uploader.upload_document = AsyncMock(return_value='doc_123')
    uploader.upload_batch = AsyncMock(return_value=['doc_1', 'doc_2'])
    uploader.get_upload_stats = Mock(return_value={
        'total_uploads': 5,
        'successful_uploads': 4,
        'failed_uploads': 1,
        'success_rate': 0.8
    })
    return uploader


class TestProdStorageManager:
    """Test cases for Production Storage Manager"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, sample_config, mock_rag_uploader):
        """Test successful initialization"""
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            
            assert storage.is_initialized()
            mock_rag_uploader.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, sample_config, mock_rag_uploader):
        """Test cleanup"""
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            await storage.cleanup()
            
            mock_rag_uploader.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_document_success(self, sample_config, sample_document, mock_rag_uploader):
        """Test successful document save"""
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            
            doc_id = await storage.save_document(sample_document, 'agriculture')
            
            assert doc_id == 'doc_123'
            mock_rag_uploader.upload_document.assert_called_once_with(sample_document, 'agriculture')
            
            # Check tracking
            assert len(storage.uploaded_documents['agriculture']) == 1
            assert storage.uploaded_documents['agriculture'][0]['doc_id'] == 'doc_123'
    
    @pytest.mark.asyncio
    async def test_save_document_invalid_domain(self, sample_config, sample_document, mock_rag_uploader):
        """Test save document with invalid domain defaults to agriculture"""
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            
            doc_id = await storage.save_document(sample_document, 'invalid_domain')
            
            assert doc_id == 'doc_123'
            # Should have called with agriculture domain
            mock_rag_uploader.upload_document.assert_called_once_with(sample_document, 'agriculture')
    
    @pytest.mark.asyncio
    async def test_save_document_error_handling(self, sample_config, sample_document, mock_rag_uploader):
        """Test error handling during document save"""
        mock_rag_uploader.upload_document.side_effect = Exception("Upload failed")
        
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            
            with pytest.raises(Exception, match="Upload failed"):
                await storage.save_document(sample_document, 'agriculture')
    
    @pytest.mark.asyncio
    async def test_save_media_catalog(self, sample_config, mock_rag_uploader):
        """Test saving media catalog"""
        catalog_content = "# Media Catalog\n\n- image1.jpg\n- document.pdf"
        source_url = "https://example.com"
        
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            
            doc_id = await storage.save_media_catalog(catalog_content, 'agriculture', source_url)
            
            assert doc_id == 'doc_123'
            mock_rag_uploader.upload_document.assert_called_once()
            
            # Check that a ScrapedDocument was created for the catalog
            call_args = mock_rag_uploader.upload_document.call_args
            catalog_doc = call_args[0][0]
            assert catalog_doc.title == f"Media Catalog - {source_url}"
            assert catalog_doc.markdown == catalog_content
            assert catalog_doc.metadata['type'] == 'media_catalog'
            
            # Check tracking
            assert len(storage.uploaded_documents['agriculture']) == 1
            assert storage.uploaded_documents['agriculture'][0]['type'] == 'media_catalog'
    
    @pytest.mark.asyncio
    async def test_upload_batch_to_domain(self, sample_config, sample_document, mock_rag_uploader):
        """Test batch upload to domain"""
        documents = [sample_document, sample_document]
        
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            
            doc_ids = await storage.upload_batch_to_domain(documents, 'agriculture')
            
            assert doc_ids == ['doc_1', 'doc_2']
            mock_rag_uploader.upload_batch.assert_called_once_with(documents, 'agriculture')
            
            # Check tracking
            assert len(storage.uploaded_documents['agriculture']) == 2
    
    @pytest.mark.asyncio
    async def test_upload_batch_partial_success(self, sample_config, sample_document, mock_rag_uploader):
        """Test batch upload with partial success"""
        documents = [sample_document, sample_document]
        mock_rag_uploader.upload_batch.return_value = ['doc_1', None]  # Second upload failed
        
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            
            doc_ids = await storage.upload_batch_to_domain(documents, 'agriculture')
            
            assert doc_ids == ['doc_1', None]
            
            # Check tracking - only successful upload should be tracked
            assert len(storage.uploaded_documents['agriculture']) == 1
            assert storage.uploaded_documents['agriculture'][0]['doc_id'] == 'doc_1'
    
    @pytest.mark.asyncio
    async def test_upload_multi_domain(self, sample_config, sample_document, mock_rag_uploader):
        """Test uploading to multiple domains"""
        domains = ['agriculture', 'water', 'weather']
        mock_rag_uploader.upload_document.side_effect = ['doc_agri', 'doc_water', 'doc_weather']
        
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            
            results = await storage.upload_multi_domain(sample_document, domains)
            
            expected_results = {
                'agriculture': 'doc_agri',
                'water': 'doc_water',
                'weather': 'doc_weather'
            }
            assert results == expected_results
            
            # Check tracking for all domains
            assert len(storage.uploaded_documents['agriculture']) == 1
            assert len(storage.uploaded_documents['water']) == 1
            assert len(storage.uploaded_documents['weather']) == 1
    
    @pytest.mark.asyncio
    async def test_upload_multi_domain_partial_failure(self, sample_config, sample_document, mock_rag_uploader):
        """Test multi-domain upload with partial failure"""
        domains = ['agriculture', 'water']
        
        def upload_side_effect(doc, domain):
            if domain == 'agriculture':
                return 'doc_agri'
            else:
                raise Exception("Upload failed")
        
        mock_rag_uploader.upload_document.side_effect = upload_side_effect
        
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            await storage.initialize()
            
            results = await storage.upload_multi_domain(sample_document, domains)
            
            expected_results = {
                'agriculture': 'doc_agri',
                'water': None
            }
            assert results == expected_results
            
            # Check tracking - only successful upload should be tracked
            assert len(storage.uploaded_documents['agriculture']) == 1
            assert len(storage.uploaded_documents['water']) == 0
    
    def test_create_domain_structure(self, sample_config, mock_rag_uploader):
        """Test domain structure creation"""
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            storage.create_domain_structure()
            
            # Should initialize tracking for all domains
            for domain in storage.domains:
                assert domain in storage.uploaded_documents
                assert storage.uploaded_documents[domain] == []
    
    def test_get_storage_stats(self, sample_config, mock_rag_uploader):
        """Test storage statistics generation"""
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            
            # Add some test data
            storage.uploaded_documents['agriculture'] = [
                {'doc_id': 'doc_1', 'type': 'document'},
                {'doc_id': 'doc_2', 'type': 'media_catalog'},
                {'doc_id': 'doc_3', 'type': 'document'}
            ]
            storage.uploaded_documents['water'] = [
                {'doc_id': 'doc_4', 'type': 'document'}
            ]
            
            stats = storage.get_storage_stats()
            
            assert stats['mode'] == 'production'
            assert stats['total_documents'] == 3  # 2 agriculture + 1 water
            assert stats['total_media_catalogs'] == 1
            assert stats['domains']['agriculture']['documents'] == 2
            assert stats['domains']['agriculture']['media_catalogs'] == 1
            assert stats['domains']['water']['documents'] == 1
            assert stats['domains']['water']['media_catalogs'] == 0
            assert 'rag_uploader_stats' in stats
    
    def test_get_domain_document_count(self, sample_config, mock_rag_uploader):
        """Test getting document count for domain"""
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            
            # Add test data
            storage.uploaded_documents['agriculture'] = [
                {'doc_id': 'doc_1'},
                {'doc_id': 'doc_2'},
                {'doc_id': 'doc_3'}
            ]
            
            count = storage.get_domain_document_count('agriculture')
            assert count == 3
            
            count = storage.get_domain_document_count('water')
            assert count == 0
    
    def test_get_recent_uploads(self, sample_config, mock_rag_uploader):
        """Test getting recent uploads for domain"""
        with patch('scraper.storage.prod_storage.RAGUploader', return_value=mock_rag_uploader):
            storage = ProdStorageManager(sample_config)
            
            # Add test data
            test_uploads = [
                {'doc_id': f'doc_{i}', 'title': f'Document {i}'}
                for i in range(15)
            ]
            storage.uploaded_documents['agriculture'] = test_uploads
            
            # Get recent uploads (default limit 10)
            recent = storage.get_recent_uploads('agriculture')
            assert len(recent) == 10
            assert recent[0]['doc_id'] == 'doc_5'  # Last 10 items
            assert recent[-1]['doc_id'] == 'doc_14'
            
            # Get recent uploads with custom limit
            recent = storage.get_recent_uploads('agriculture', limit=5)
            assert len(recent) == 5
            assert recent[0]['doc_id'] == 'doc_10'  # Last 5 items
            assert recent[-1]['doc_id'] == 'doc_14'
            
            # Test empty domain
            recent = storage.get_recent_uploads('water')
            assert recent == []


if __name__ == '__main__':
    pytest.main([__file__])