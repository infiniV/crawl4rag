"""
Integration tests for RAG API components

Tests the integration between RAG uploader and production storage manager
to ensure they work together correctly.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from scraper.storage.rag_uploader import RAGUploader
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
def sample_documents():
    """Sample scraped documents for testing"""
    docs = []
    
    for i in range(3):
        doc = ScrapedDocument(
            url=f'https://example.com/test-{i}',
            title=f'Test Document {i+1}',
            content=f'This is test content for document {i+1}',
            markdown=f'# Test Document {i+1}\n\nThis is test content for document {i+1}',
            metadata={'source': 'test', 'index': i},
            media_catalog=[],
            domain_classifications=['agriculture'],
            timestamp=datetime.now(),
            content_hash=f'test_hash_{i}',
            processing_time=1.0 + i * 0.5,
            retry_count=0
        )
        docs.append(doc)
    
    return docs


class TestRAGIntegration:
    """Integration tests for RAG API components"""
    
    @pytest.mark.asyncio
    async def test_production_storage_with_rag_uploader(self, sample_config, sample_documents):
        """Test production storage manager using RAG uploader"""
        with patch.dict('os.environ', {'TEST_RAG_API_KEY': 'test_key'}):
            with patch('aiohttp.ClientSession') as mock_session_class:
                # Mock HTTP session
                mock_session = AsyncMock()
                mock_session.headers = {}
                mock_session_class.return_value = mock_session
                
                # Mock authentication response
                auth_response = AsyncMock()
                auth_response.status = 200
                auth_response.json.return_value = {
                    'access_token': 'test_token',
                    'expires_in': 3600
                }
                
                # Mock upload responses
                upload_responses = []
                for i in range(len(sample_documents)):
                    response = AsyncMock()
                    response.status = 201
                    response.json.return_value = {'document_id': f'doc_{i}'}
                    upload_responses.append(response)
                
                # Set up mock responses
                mock_session.post.return_value.__aenter__.side_effect = [
                    auth_response,  # Authentication
                    *upload_responses  # Document uploads
                ]
                
                # Initialize production storage
                storage = ProdStorageManager(sample_config)
                await storage.initialize()
                
                # Test single document upload
                doc_id = await storage.save_document(sample_documents[0], 'agriculture')
                assert doc_id == 'doc_0'
                
                # Verify tracking
                assert len(storage.uploaded_documents['agriculture']) == 1
                assert storage.uploaded_documents['agriculture'][0]['doc_id'] == 'doc_0'
                
                # Test batch upload
                remaining_docs = sample_documents[1:]
                with patch.object(storage.rag_uploader, 'upload_batch') as mock_batch:
                    mock_batch.return_value = ['doc_1', 'doc_2']
                    
                    doc_ids = await storage.upload_batch_to_domain(remaining_docs, 'water')
                    assert doc_ids == ['doc_1', 'doc_2']
                    
                    # Verify batch upload was called
                    mock_batch.assert_called_once_with(remaining_docs, 'water')
                
                # Test storage statistics
                stats = storage.get_storage_stats()
                assert stats['mode'] == 'production'
                assert stats['total_documents'] >= 1  # At least one document uploaded
                
                await storage.cleanup()
    
    @pytest.mark.asyncio
    async def test_multi_domain_upload_integration(self, sample_config, sample_documents):
        """Test multi-domain upload functionality"""
        with patch.dict('os.environ', {'TEST_RAG_API_KEY': 'test_key'}):
            with patch('aiohttp.ClientSession') as mock_session_class:
                # Mock HTTP session
                mock_session = AsyncMock()
                mock_session.headers = {}
                mock_session_class.return_value = mock_session
                
                # Mock authentication
                auth_response = AsyncMock()
                auth_response.status = 200
                auth_response.json.return_value = {
                    'access_token': 'test_token',
                    'expires_in': 3600
                }
                
                # Mock multiple domain uploads
                domain_responses = []
                domains = ['agriculture', 'water', 'weather']
                for i, domain in enumerate(domains):
                    response = AsyncMock()
                    response.status = 201
                    response.json.return_value = {'document_id': f'doc_{domain}_{i}'}
                    domain_responses.append(response)
                
                mock_session.post.return_value.__aenter__.side_effect = [
                    auth_response,  # Authentication
                    *domain_responses  # Domain uploads
                ]
                
                # Initialize storage
                storage = ProdStorageManager(sample_config)
                await storage.initialize()
                
                # Test multi-domain upload
                document = sample_documents[0]
                results = await storage.upload_multi_domain(document, domains)
                
                # Verify results
                expected_results = {
                    'agriculture': 'doc_agriculture_0',
                    'water': 'doc_water_1',
                    'weather': 'doc_weather_2'
                }
                assert results == expected_results
                
                # Verify tracking in all domains
                for domain in domains:
                    assert len(storage.uploaded_documents[domain]) == 1
                
                await storage.cleanup()
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, sample_config, sample_documents):
        """Test error handling in integrated components"""
        with patch.dict('os.environ', {'TEST_RAG_API_KEY': 'test_key'}):
            with patch('aiohttp.ClientSession') as mock_session_class:
                # Mock HTTP session
                mock_session = AsyncMock()
                mock_session.headers = {}
                mock_session_class.return_value = mock_session
                
                # Mock authentication success
                auth_response = AsyncMock()
                auth_response.status = 200
                auth_response.json.return_value = {
                    'access_token': 'test_token',
                    'expires_in': 3600
                }
                
                # Mock upload failure
                failure_response = AsyncMock()
                failure_response.status = 500
                failure_response.text.return_value = 'Internal Server Error'
                
                mock_session.post.return_value.__aenter__.side_effect = [
                    auth_response,  # Authentication
                    failure_response,  # Upload failure
                    failure_response,  # Retry failure
                    failure_response,  # Final failure
                    failure_response   # Max retries exceeded
                ]
                
                # Initialize storage
                storage = ProdStorageManager(sample_config)
                await storage.initialize()
                
                # Test error handling
                with patch('asyncio.sleep'):  # Speed up retries
                    with pytest.raises(Exception):
                        await storage.save_document(sample_documents[0], 'agriculture')
                
                # Verify no documents were tracked due to failure
                assert len(storage.uploaded_documents['agriculture']) == 0
                
                await storage.cleanup()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, sample_config, sample_documents):
        """Test rate limiting behavior in integrated system"""
        with patch.dict('os.environ', {'TEST_RAG_API_KEY': 'test_key'}):
            with patch('aiohttp.ClientSession') as mock_session_class:
                # Mock HTTP session
                mock_session = AsyncMock()
                mock_session.headers = {}
                mock_session_class.return_value = mock_session
                
                # Mock authentication
                auth_response = AsyncMock()
                auth_response.status = 200
                auth_response.json.return_value = {
                    'access_token': 'test_token',
                    'expires_in': 3600
                }
                
                # Mock rate limiting then success
                rate_limit_response = AsyncMock()
                rate_limit_response.status = 429
                rate_limit_response.headers = {'Retry-After': '1'}
                
                success_response = AsyncMock()
                success_response.status = 201
                success_response.json.return_value = {'document_id': 'doc_after_rate_limit'}
                
                mock_session.post.return_value.__aenter__.side_effect = [
                    auth_response,  # Authentication
                    rate_limit_response,  # Rate limited
                    success_response  # Success after waiting
                ]
                
                # Initialize storage
                storage = ProdStorageManager(sample_config)
                await storage.initialize()
                
                # Test rate limiting handling
                with patch('asyncio.sleep') as mock_sleep:
                    doc_id = await storage.save_document(sample_documents[0], 'agriculture')
                    
                    # Verify success after rate limiting
                    assert doc_id == 'doc_after_rate_limit'
                    
                    # Verify sleep was called for rate limiting
                    mock_sleep.assert_called_with(1)
                
                # Verify statistics include rate limit hit
                uploader_stats = storage.rag_uploader.get_upload_stats()
                assert uploader_stats['rate_limit_hits'] == 1
                
                await storage.cleanup()
    
    def test_configuration_validation(self, sample_config):
        """Test configuration validation across components"""
        # Test valid configuration
        storage = ProdStorageManager(sample_config)
        assert storage.rag_uploader.api_url == 'http://test-api.example.com'
        assert storage.rag_uploader.api_key_env == 'TEST_RAG_API_KEY'
        
        # Test configuration with missing values
        invalid_config = {'storage': {'prod': {}}}
        storage_invalid = ProdStorageManager(invalid_config)
        
        # Should use defaults
        assert storage_invalid.rag_uploader.api_url == 'http://217.154.66.145:8000'
        assert storage_invalid.rag_uploader.api_key_env == 'RAG_API_KEY'
    
    def test_domain_mapping_consistency(self, sample_config):
        """Test that domain mappings are consistent across components"""
        storage = ProdStorageManager(sample_config)
        uploader = RAGUploader(sample_config['storage'])
        
        # Verify both components have the same domain lists
        assert storage.domains == list(uploader.domain_endpoints.keys())
        
        # Verify all expected domains are present
        expected_domains = [
            'agriculture', 'water', 'weather', 'crops',
            'farm', 'marketplace', 'banking', 'chat'
        ]
        
        for domain in expected_domains:
            assert domain in storage.domains
            assert domain in uploader.domain_endpoints
    
    @pytest.mark.asyncio
    async def test_media_catalog_upload_integration(self, sample_config):
        """Test media catalog upload through production storage"""
        with patch.dict('os.environ', {'TEST_RAG_API_KEY': 'test_key'}):
            with patch('aiohttp.ClientSession') as mock_session_class:
                # Mock HTTP session
                mock_session = AsyncMock()
                mock_session.headers = {}
                mock_session_class.return_value = mock_session
                
                # Mock responses
                auth_response = AsyncMock()
                auth_response.status = 200
                auth_response.json.return_value = {
                    'access_token': 'test_token',
                    'expires_in': 3600
                }
                
                catalog_response = AsyncMock()
                catalog_response.status = 201
                catalog_response.json.return_value = {'document_id': 'catalog_123'}
                
                mock_session.post.return_value.__aenter__.side_effect = [
                    auth_response,
                    catalog_response
                ]
                
                # Initialize storage
                storage = ProdStorageManager(sample_config)
                await storage.initialize()
                
                # Test media catalog upload
                catalog_content = "# Media Catalog\n\n- image1.jpg\n- document.pdf"
                source_url = "https://example.com/test"
                
                catalog_id = await storage.save_media_catalog(
                    catalog_content, 'agriculture', source_url
                )
                
                assert catalog_id == 'catalog_123'
                
                # Verify catalog was tracked
                agriculture_docs = storage.uploaded_documents['agriculture']
                assert len(agriculture_docs) == 1
                assert agriculture_docs[0]['type'] == 'media_catalog'
                assert agriculture_docs[0]['doc_id'] == 'catalog_123'
                
                await storage.cleanup()


if __name__ == '__main__':
    pytest.main([__file__])