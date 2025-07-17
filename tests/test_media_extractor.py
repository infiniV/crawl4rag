"""
Tests for Media Extractor Implementation

Tests media extraction, file downloads, and organized storage
with resumable downloads and error recovery.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
from aioresponses import aioresponses

from scraper.processors.media import MediaExtractor
from scraper.core.base import CrawlResult, MediaItem
from scraper.core.logging import setup_logging


class TestMediaExtractor:
    """Test cases for MediaExtractor"""
    
    @pytest.fixture(autouse=True)
    def setup_logging(self):
        """Set up logging for tests"""
        setup_logging(level="DEBUG", log_file="./logs/test_scraper.log")
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config(self, temp_dir):
        """Test configuration"""
        return {
            'files_path': temp_dir,
            'max_file_size': 1024 * 1024,  # 1MB for testing
            'download_timeout': 10,
            'max_download_retries': 2,
            'retry_delay': 0.1,
            'concurrent_downloads': 2
        }
    
    @pytest.fixture
    def media_extractor(self, config):
        """Create MediaExtractor instance"""
        return MediaExtractor(config)
    
    @pytest.fixture
    def sample_html(self):
        """Sample HTML with various media elements"""
        return """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <img src="image1.jpg" alt="Test Image 1" width="100" height="200">
            <img src="/images/image2.png" alt="Test Image 2">
            <img src="https://example.com/image3.gif" alt="External Image">
            
            <a href="document.pdf">Download PDF</a>
            <a href="/files/spreadsheet.xlsx">Excel File</a>
            <a href="https://example.com/archive.zip">Download Archive</a>
            
            <video src="video1.mp4" controls>
                <source src="video2.webm" type="video/webm">
            </video>
            
            <audio src="audio1.mp3" controls>
                <source src="audio2.ogg" type="audio/ogg">
            </audio>
        </body>
        </html>
        """
    
    @pytest.fixture
    def sample_crawl_result(self, sample_html):
        """Sample crawl result"""
        return CrawlResult(
            url="https://example.com/test-page",
            html=sample_html,
            markdown="# Test Page\n\nSample content",
            links=["https://example.com/link1", "https://example.com/link2"],
            media=[
                {
                    'url': 'image1.jpg',
                    'alt': 'Crawl4AI Image',
                    'type': 'image/jpeg',
                    'size': 12345
                },
                {
                    'url': '/files/document.pdf',
                    'type': 'application/pdf',
                    'size': 54321
                }
            ],
            metadata={'title': 'Test Page'},
            success=True
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, media_extractor, temp_dir):
        """Test MediaExtractor initialization"""
        await media_extractor.initialize()
        assert media_extractor.is_initialized()
        
        # Check that storage directories are created
        base_path = Path(temp_dir)
        expected_dirs = ['images', 'documents', 'archives', 'videos', 'audio', 'other']
        
        for directory in expected_dirs:
            assert (base_path / directory).exists()
            assert (base_path / directory).is_dir()
    
    def test_determine_file_type(self, media_extractor):
        """Test file type determination"""
        # Test with media data
        media_data = {'type': 'image/jpeg'}
        assert media_extractor._determine_file_type('test.jpg', media_data) == 'image'
        
        media_data = {'type': 'application/pdf'}
        assert media_extractor._determine_file_type('test.pdf', media_data) == 'document'
        
        # Test with URL extensions
        assert media_extractor._determine_file_type('https://example.com/image.png') == 'image'
        assert media_extractor._determine_file_type('https://example.com/doc.pdf') == 'document'
        assert media_extractor._determine_file_type('https://example.com/archive.zip') == 'archive'
        assert media_extractor._determine_file_type('https://example.com/video.mp4') == 'video'
        assert media_extractor._determine_file_type('https://example.com/audio.mp3') == 'audio'
        assert media_extractor._determine_file_type('https://example.com/unknown.xyz') == 'other'
    
    def test_categorize_media_item(self, media_extractor):
        """Test media item categorization"""
        # Test different media types
        image_item = MediaItem(url="test.jpg", type="image")
        assert media_extractor._categorize_media_item(image_item) == 'images'
        
        doc_item = MediaItem(url="test.pdf", type="document")
        assert media_extractor._categorize_media_item(doc_item) == 'documents'
        
        video_item = MediaItem(url="test.mp4", type="video")
        assert media_extractor._categorize_media_item(video_item) == 'videos'
        
        other_item = MediaItem(url="test.xyz", type="other")
        assert media_extractor._categorize_media_item(other_item) == 'other'
    
    def test_extract_media_urls(self, media_extractor, sample_crawl_result):
        """Test media URL extraction from crawl result"""
        media_items = media_extractor.extract_media_urls(sample_crawl_result)
        
        # Check that all categories are present
        expected_categories = ['images', 'documents', 'archives', 'videos', 'audio', 'other']
        assert all(category in media_items for category in expected_categories)
        
        # Check that we have extracted items
        assert len(media_items['images']) > 0
        assert len(media_items['documents']) > 0
        assert len(media_items['videos']) > 0
        assert len(media_items['audio']) > 0
        
        # Check specific items
        image_urls = [item.url for item in media_items['images']]
        assert any('image1.jpg' in url for url in image_urls)
        assert any('image2.png' in url for url in image_urls)
        assert any('image3.gif' in url for url in image_urls)
        
        # Check that URLs are properly resolved
        absolute_urls = [item.url for item in media_items['images'] if item.url.startswith('https://')]
        assert len(absolute_urls) > 0
    
    def test_create_media_item_from_crawl_data(self, media_extractor):
        """Test creating MediaItem from crawl4ai data"""
        media_data = {
            'url': 'image.jpg',
            'alt': 'Test Image',
            'type': 'image/jpeg',
            'size': 12345
        }
        base_url = 'https://example.com/page'
        
        media_item = media_extractor._create_media_item_from_crawl_data(media_data, base_url)
        
        assert media_item is not None
        assert media_item.url == 'https://example.com/image.jpg'
        assert media_item.type == 'image'
        assert media_item.alt_text == 'Test Image'
        assert media_item.file_size == 12345
        assert media_item.metadata['source_url'] == base_url
        assert media_item.metadata['extraction_method'] == 'crawl4ai'
    
    def test_extract_media_from_html(self, media_extractor, sample_html):
        """Test media extraction from HTML"""
        base_url = 'https://example.com/page'
        media_items = media_extractor._extract_media_from_html(sample_html, base_url)
        
        # Check images
        assert len(media_items['images']) >= 3
        image_alts = [item.alt_text for item in media_items['images']]
        assert 'Test Image 1' in image_alts
        assert 'Test Image 2' in image_alts
        
        # Check documents (from links)
        doc_items = media_items['documents']
        doc_urls = [item.url for item in doc_items]
        assert any('document.pdf' in url for url in doc_urls)
        assert any('spreadsheet.xlsx' in url for url in doc_urls)
        
        # Check videos
        assert len(media_items['videos']) >= 2  # video src + source tag
        
        # Check audio
        assert len(media_items['audio']) >= 2  # audio src + source tag
    
    def test_create_media_catalog(self, media_extractor):
        """Test media catalog creation"""
        # Create sample media data
        media_data = {
            'images': [
                MediaItem(url='https://example.com/image1.jpg', type='image', alt_text='Image 1', file_size=1000, download_status='completed'),
                MediaItem(url='https://example.com/image2.png', type='image', alt_text='Image 2', download_status='pending')
            ],
            'documents': [
                MediaItem(url='https://example.com/doc.pdf', type='document', alt_text='Document', file_size=5000, download_status='completed')
            ],
            'archives': [],
            'videos': [],
            'audio': [],
            'other': []
        }
        
        catalog = media_extractor.create_media_catalog(media_data)
        
        # Check catalog structure
        assert '# Media Catalog' in catalog
        assert '**Total Media Items:** 3' in catalog
        assert '## Images (2 items)' in catalog
        assert '## Documents (1 items)' in catalog
        assert 'https://example.com/image1.jpg' in catalog
        assert 'https://example.com/doc.pdf' in catalog
        
        # Check statistics section
        assert '## Metadata' in catalog
        assert 'Download Statistics' in catalog
    
    def test_generate_filename(self, media_extractor):
        """Test filename generation"""
        # Test normal URL with filename
        filename = media_extractor._generate_filename('https://example.com/path/image.jpg')
        assert filename == 'image.jpg'
        
        # Test URL without filename
        filename = media_extractor._generate_filename('https://example.com/path/')
        assert filename.startswith('file_')
        assert filename.endswith('.bin')
        
        # Test URL with query parameters
        filename = media_extractor._generate_filename('https://example.com/image.jpg?v=123')
        assert filename == 'image.jpg'
        
        # Test filename sanitization
        filename = media_extractor._generate_filename('https://example.com/bad<>name.jpg')
        assert '<' not in filename
        assert '>' not in filename
    
    @pytest.mark.asyncio
    async def test_download_single_file_success(self, media_extractor, temp_dir):
        """Test successful single file download"""
        media_item = MediaItem(
            url='https://example.com/test.jpg',
            type='image',
            file_size=100
        )
        
        # Mock the download
        test_content = b'fake image content' * 5  # This is actually 90 bytes
        with aioresponses() as m:
            m.get('https://example.com/test.jpg', 
                  body=test_content,
                  headers={'content-length': str(len(test_content))})
            
            semaphore = asyncio.Semaphore(1)
            result = await media_extractor._download_single_file(media_item, temp_dir, semaphore)
            
            assert result is not None
            assert Path(result).exists()
            assert Path(result).stat().st_size == len(test_content)
    
    @pytest.mark.asyncio
    async def test_download_single_file_retry(self, media_extractor, temp_dir):
        """Test file download with retry logic"""
        media_item = MediaItem(
            url='https://example.com/test.jpg',
            type='image'
        )
        
        with aioresponses() as m:
            # First attempt fails
            m.get('https://example.com/test.jpg', status=500)
            # Second attempt succeeds
            m.get('https://example.com/test.jpg', 
                  body=b'fake image content',
                  headers={'content-length': '18'})
            
            semaphore = asyncio.Semaphore(1)
            result = await media_extractor._download_single_file(media_item, temp_dir, semaphore)
            
            assert result is not None
            assert Path(result).exists()
    
    @pytest.mark.asyncio
    async def test_download_single_file_too_large(self, media_extractor, temp_dir):
        """Test file download size limit"""
        media_item = MediaItem(
            url='https://example.com/large.jpg',
            type='image'
        )
        
        # Set a small max file size for testing
        media_extractor.max_file_size = 50
        
        with aioresponses() as m:
            m.get('https://example.com/large.jpg', 
                  body=b'x' * 100,  # 100 bytes, exceeds limit
                  headers={'content-length': '100'})
            
            semaphore = asyncio.Semaphore(1)
            result = await media_extractor._download_single_file(media_item, temp_dir, semaphore)
            
            assert result is None  # Should fail due to size limit
    
    @pytest.mark.asyncio
    async def test_download_files_batch(self, media_extractor, temp_dir):
        """Test batch file download"""
        media_items = [
            MediaItem(url='https://example.com/file1.jpg', type='image'),
            MediaItem(url='https://example.com/file2.pdf', type='document'),
            MediaItem(url='https://example.com/file3.png', type='image')
        ]
        
        with aioresponses() as m:
            for item in media_items:
                m.get(item.url, 
                      body=b'fake content',
                      headers={'content-length': '12'})
            
            results = await media_extractor.download_files(media_items, temp_dir)
            
            assert len(results) == 3
            for result in results:
                assert Path(result).exists()
            
            # Check that media items were updated
            for item in media_items:
                assert item.download_status == 'completed'
                assert item.local_path is not None
    
    def test_organize_files(self, media_extractor, temp_dir):
        """Test file organization by domain and type"""
        # Create test files
        test_files = []
        for filename in ['image.jpg', 'document.pdf', 'archive.zip', 'video.mp4']:
            file_path = Path(temp_dir) / filename
            file_path.write_text('test content')
            test_files.append(str(file_path))
        
        source_domain = 'example.com'
        media_extractor.organize_files(test_files, source_domain)
        
        # Check domain directory structure
        domain_dir = Path(temp_dir) / source_domain
        assert domain_dir.exists()
        
        # Check type directories
        type_dirs = ['images', 'documents', 'archives', 'videos', 'audio', 'other']
        for type_dir in type_dirs:
            assert (domain_dir / type_dir).exists()
        
        # Check that files were moved to correct directories
        assert (domain_dir / 'images' / 'image.jpg').exists()
        assert (domain_dir / 'documents' / 'document.pdf').exists()
        assert (domain_dir / 'archives' / 'archive.zip').exists()
        assert (domain_dir / 'videos' / 'video.mp4').exists()
        
        # Check that original files were moved (not copied)
        for file_path in test_files:
            assert not Path(file_path).exists()
    
    @pytest.mark.asyncio
    async def test_resumable_download(self, media_extractor, temp_dir):
        """Test resumable download functionality"""
        media_item = MediaItem(
            url='https://example.com/large.jpg',
            type='image',
            file_size=200
        )
        
        filename = media_extractor._generate_filename(media_item.url)
        filepath = Path(temp_dir) / filename
        
        # Create partial file
        filepath.write_bytes(b'partial content')
        partial_size = filepath.stat().st_size
        
        with aioresponses() as m:
            # Mock resumable download response
            remaining_content = b'remaining content'
            m.get('https://example.com/large.jpg',
                  body=remaining_content,
                  status=206,  # Partial content
                  headers={'content-length': str(len(remaining_content))})
            
            semaphore = asyncio.Semaphore(1)
            result = await media_extractor._download_single_file(media_item, temp_dir, semaphore)
            
            assert result is not None
            assert Path(result).exists()
            
            # Check that file contains both partial and remaining content
            final_content = Path(result).read_bytes()
            assert final_content.startswith(b'partial content')
            assert final_content.endswith(b'remaining content')
    
    @pytest.mark.asyncio
    async def test_cleanup(self, media_extractor):
        """Test cleanup functionality"""
        await media_extractor.initialize()
        await media_extractor.cleanup()
        # Should not raise any exceptions


if __name__ == '__main__':
    pytest.main([__file__])