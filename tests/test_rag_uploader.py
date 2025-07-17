"""
Tests for RAG API Uploader

Tests authentication, document upload, batch operations, rate limiting,
and error handling for the RAG API integration.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import aiohttp
import json

from scraper.storage.rag_uploader import RAGUploader
from scraper.core.base import ScrapedDocument, APIError


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        'prod': {
            'rag_api_url': 'http://test-api.example.com',
            'api_key_env': 'TEST_RAG_API_KEY'
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
def mock_session():
    """Mock aiohttp session"""
    session = AsyncMock()
    session.headers = {}
    return session


class TestRAGUploader:
    """Test cases for RAG API Uploader"""
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, sample_config):
        """Test successful initialization"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session.headers = {}
                mock_session_class.return_value = mock_session
                
                # Mock successful authentication
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = {
                    'access_token': 'test_token',
                    'expires_in': 3600
                }
                mock_session.post.return_value.__aenter__.return_value = mock_response
                
                uploader = RAGUploader(sample_config)
                await uploader.initialize()
                
                assert uploader.is_initialized()
                assert uploader.auth_token == 'test_token'
                assert uploader.api_key == 'test_key'
                
                await uploader.cleanup()
    
    @pytest.mark.asyncio
    async def test_initialization_missing_api_key(self, sample_config):
        """Test initialization failure with missing API key"""
        with patch.dict(os.environ, {}, clear=True):
            uploader = RAGUploader(sample_config)
            
            with pytest.raises(APIError, match="API key not found"):
                await uploader.initialize()
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self, sample_config):
        """Test authentication failure"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session.headers = {}
                mock_session_class.return_value = mock_session
                
                # Mock failed authentication
                mock_response = AsyncMock()
                mock_response.status = 401
                mock_response.text.return_value = 'Unauthorized'
                mock_session.post.return_value.__aenter__.return_value = mock_response
                
                uploader = RAGUploader(sample_config)
                
                with pytest.raises(APIError, match="Failed to authenticate"):
                    await uploader.initialize()
    
    @pytest.mark.asyncio
    async def test_upload_document_success(self, sample_config, sample_document):
        """Test successful document upload"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            uploader = RAGUploader(sample_config)
            uploader.session = AsyncMock()
            uploader.session.headers = {}
            uploader.auth_token = 'test_token'
            uploader.token_expires_at = datetime.now() + timedelta(hours=1)
            uploader._initialized = True
            
            # Mock successful upload
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json.return_value = {'document_id': 'doc_123'}
            uploader.session.post.return_value.__aenter__.return_value = mock_response
            
            doc_id = await uploader.upload_document(sample_document, 'agriculture')
            
            assert doc_id == 'doc_123'
            assert uploader.upload_stats['successful_uploads'] == 1
            assert uploader.upload_stats['domains']['agriculture']['successes'] == 1
    
    @pytest.mark.asyncio
    async def test_upload_document_invalid_domain(self, sample_config, sample_document):
        """Test upload with invalid domain defaults to agriculture"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            uploader = RAGUploader(sample_config)
            uploader.session = AsyncMock()
            uploader.session.headers = {}
            uploader.auth_token = 'test_token'
            uploader.token_expires_at = datetime.now() + timedelta(hours=1)
            uploader._initialized = True
            
            # Mock successful upload
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json.return_value = {'document_id': 'doc_123'}
            uploader.session.post.return_value.__aenter__.return_value = mock_response
            
            doc_id = await uploader.upload_document(sample_document, 'invalid_domain')
            
            assert doc_id == 'doc_123'
            # Should have uploaded to agriculture domain
            uploader.session.post.assert_called_once()
            call_args = uploader.session.post.call_args
            assert '/api/v1/documents/agriculture' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_upload_document_rate_limited(self, sample_config, sample_document):
        """Test handling of rate limiting"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            uploader = RAGUploader(sample_config)
            uploader.session = AsyncMock()
            uploader.session.headers = {}
            uploader.auth_token = 'test_token'
            uploader.token_expires_at = datetime.now() + timedelta(hours=1)
            uploader._initialized = True
            
            # Mock rate limited response then success
            rate_limit_response = AsyncMock()
            rate_limit_response.status = 429
            rate_limit_response.headers = {'Retry-After': '1'}
            
            success_response = AsyncMock()
            success_response.status = 201
            success_response.json.return_value = {'document_id': 'doc_123'}
            
            uploader.session.post.return_value.__aenter__.side_effect = [
                rate_limit_response,
                success_response
            ]
            
            with patch('asyncio.sleep') as mock_sleep:
                doc_id = await uploader.upload_document(sample_document, 'agriculture')
                
                assert doc_id == 'doc_123'
                assert uploader.upload_stats['rate_limit_hits'] == 1
                mock_sleep.assert_called_with(1)
    
    @pytest.mark.asyncio
    async def test_upload_document_retry_logic(self, sample_config, sample_document):
        """Test retry logic with exponential backoff"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            uploader = RAGUploader(sample_config)
            uploader.session = AsyncMock()
            uploader.session.headers = {}
            uploader.auth_token = 'test_token'
            uploader.token_expires_at = datetime.now() + timedelta(hours=1)
            uploader._initialized = True
            uploader.max_retries = 2
            
            # Mock failure then success
            failure_response = AsyncMock()
            failure_response.status = 500
            failure_response.text.return_value = 'Internal Server Error'
            
            success_response = AsyncMock()
            success_response.status = 201
            success_response.json.return_value = {'document_id': 'doc_123'}
            
            uploader.session.post.return_value.__aenter__.side_effect = [
                failure_response,
                success_response
            ]
            
            with patch('asyncio.sleep') as mock_sleep:
                doc_id = await uploader.upload_document(sample_document, 'agriculture')
                
                assert doc_id == 'doc_123'
                assert uploader.upload_stats['retries'] == 1
                mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_document_max_retries_exceeded(self, sample_config, sample_document):
        """Test failure after max retries exceeded"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            uploader = RAGUploader(sample_config)
            uploader.session = AsyncMock()
            uploader.session.headers = {}
            uploader.auth_token = 'test_token'
            uploader.token_expires_at = datetime.now() + timedelta(hours=1)
            uploader._initialized = True
            uploader.max_retries = 1
            
            # Mock consistent failures
            failure_response = AsyncMock()
            failure_response.status = 500
            failure_response.text.return_value = 'Internal Server Error'
            uploader.session.post.return_value.__aenter__.return_value = failure_response
            
            with patch('asyncio.sleep'):
                with pytest.raises(APIError, match="Failed to upload document after 1 retries"):
                    await uploader.upload_document(sample_document, 'agriculture')
                
                assert uploader.upload_stats['failed_uploads'] == 1
    
    @pytest.mark.asyncio
    async def test_batch_upload_success(self, sample_config, sample_document):
        """Test successful batch upload"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            uploader = RAGUploader(sample_config)
            uploader.session = AsyncMock()
            uploader.session.headers = {}
            uploader.auth_token = 'test_token'
            uploader.token_expires_at = datetime.now() + timedelta(hours=1)
            uploader._initialized = True
            
            documents = [sample_document, sample_document]
            
            # Mock successful batch upload
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json.return_value = {'document_ids': ['doc_1', 'doc_2']}
            uploader.session.post.return_value.__aenter__.return_value = mock_response
            
            doc_ids = await uploader.upload_batch(documents, 'agriculture')
            
            assert doc_ids == ['doc_1', 'doc_2']
            assert uploader.upload_stats['successful_uploads'] == 2
    
    @pytest.mark.asyncio
    async def test_batch_upload_fallback_to_individual(self, sample_config, sample_document):
        """Test fallback to individual uploads when batch fails"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            uploader = RAGUploader(sample_config)
            uploader.session = AsyncMock()
            uploader.session.headers = {}
            uploader.auth_token = 'test_token'
            uploader.token_expires_at = datetime.now() + timedelta(hours=1)
            uploader._initialized = True
            
            documents = [sample_document, sample_document]
            
            # Mock batch upload failure
            batch_failure_response = AsyncMock()
            batch_failure_response.status = 400
            batch_failure_response.text.return_value = 'Bad Request'
            
            # Mock individual upload success
            individual_success_response = AsyncMock()
            individual_success_response.status = 201
            individual_success_response.json.return_value = {'document_id': 'doc_individual'}
            
            uploader.session.post.return_value.__aenter__.side_effect = [
                batch_failure_response,  # Batch fails
                individual_success_response,  # First individual succeeds
                individual_success_response   # Second individual succeeds
            ]
            
            with patch('asyncio.sleep'):
                doc_ids = await uploader.upload_batch(documents, 'agriculture')
                
                assert doc_ids == ['doc_individual', 'doc_individual']
    
    @pytest.mark.asyncio
    async def test_token_refresh(self, sample_config, sample_document):
        """Test automatic token refresh when token expires"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            uploader = RAGUploader(sample_config)
            uploader.session = AsyncMock()
            uploader.session.headers = {}
            uploader.auth_token = 'old_token'
            uploader.token_expires_at = datetime.now() - timedelta(minutes=1)  # Expired
            uploader._initialized = True
            
            # Mock token refresh
            auth_response = AsyncMock()
            auth_response.status = 200
            auth_response.json.return_value = {
                'access_token': 'new_token',
                'expires_in': 3600
            }
            
            # Mock successful upload
            upload_response = AsyncMock()
            upload_response.status = 201
            upload_response.json.return_value = {'document_id': 'doc_123'}
            
            uploader.session.post.return_value.__aenter__.side_effect = [
                auth_response,  # Token refresh
                upload_response  # Document upload
            ]
            
            doc_id = await uploader.upload_document(sample_document, 'agriculture')
            
            assert doc_id == 'doc_123'
            assert uploader.auth_token == 'new_token'
    
    def test_calculate_retry_delay(self, sample_config):
        """Test retry delay calculation with exponential backoff"""
        uploader = RAGUploader(sample_config)
        
        # Test exponential backoff
        delay_0 = uploader._calculate_retry_delay(0)
        delay_1 = uploader._calculate_retry_delay(1)
        delay_2 = uploader._calculate_retry_delay(2)
        
        assert 0.75 <= delay_0 <= 1.25  # Base delay with jitter
        assert 1.5 <= delay_1 <= 2.5    # 2x base delay with jitter
        assert 3.0 <= delay_2 <= 5.0    # 4x base delay with jitter
        
        # Test maximum delay cap
        delay_large = uploader._calculate_retry_delay(10)
        assert delay_large <= uploader.max_retry_delay * 1.25  # Max + jitter
    
    @pytest.mark.asyncio
    async def test_rate_limiting_wait(self, sample_config):
        """Test rate limiting wait logic"""
        uploader = RAGUploader(sample_config)
        uploader.rate_limit_requests = 2
        uploader.rate_limit_window = 60
        
        # Fill up the rate limit
        import time
        now = time.time()
        uploader.request_times = [now - 30, now - 10]  # 2 requests in window
        
        with patch('asyncio.sleep') as mock_sleep:
            with patch('time.time', return_value=now):
                await uploader._wait_for_rate_limit()
                
                # Should wait for the oldest request to age out
                mock_sleep.assert_called_once()
                wait_time = mock_sleep.call_args[0][0]
                assert 25 <= wait_time <= 35  # Should wait ~30 seconds
    
    def test_get_upload_stats(self, sample_config):
        """Test upload statistics generation"""
        uploader = RAGUploader(sample_config)
        uploader.upload_stats['start_time'] = datetime.now() - timedelta(minutes=5)
        uploader.upload_stats['total_uploads'] = 10
        uploader.upload_stats['successful_uploads'] = 8
        uploader.upload_stats['failed_uploads'] = 2
        
        stats = uploader.get_upload_stats()
        
        assert stats['total_uploads'] == 10
        assert stats['successful_uploads'] == 8
        assert stats['failed_uploads'] == 2
        assert stats['success_rate'] == 0.8
        assert 'elapsed_time' in stats
        assert 'uploads_per_minute' in stats
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, sample_config, sample_document):
        """Test handling of network errors"""
        with patch.dict(os.environ, {'TEST_RAG_API_KEY': 'test_key'}):
            uploader = RAGUploader(sample_config)
            uploader.session = AsyncMock()
            uploader.session.headers = {}
            uploader.auth_token = 'test_token'
            uploader.token_expires_at = datetime.now() + timedelta(hours=1)
            uploader._initialized = True
            uploader.max_retries = 1
            
            # Mock network error
            uploader.session.post.side_effect = aiohttp.ClientError("Network error")
            
            with patch('asyncio.sleep'):
                with pytest.raises(APIError, match="Network error during upload"):
                    await uploader.upload_document(sample_document, 'agriculture')


if __name__ == '__main__':
    pytest.main([__file__])