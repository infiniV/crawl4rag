"""
Tests for the Content Processor component

Tests HTML to markdown conversion, content quality validation,
duplicate detection, and language detection functionality.
"""

import pytest
import os
import logging
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

from scraper.processors.content import ContentProcessor
from scraper.core.base import CrawlResult, ProcessingError


# Setup logging for tests
@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Set up logging for tests"""
    from scraper.core.logging import setup_logging
    setup_logging(level="INFO", log_file="./logs/test_scraper.log")
    yield


@pytest.fixture
def content_processor():
    """Create a content processor instance for testing"""
    config = {
        'min_content_length': 50,
        'min_content_quality_score': 0.2
    }
    processor = ContentProcessor(config)
    return processor


@pytest.fixture
def sample_html():
    """Sample HTML content for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="This is a test page for content processing">
        <meta name="keywords" content="test, content, processing">
    </head>
    <body>
        <h1>Welcome to the Test Page</h1>
        <p>This is a paragraph with <strong>bold text</strong> and <em>italic text</em>.</p>
        <h2>Section 1</h2>
        <p>Here's a list of items:</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
        <h2>Section 2</h2>
        <p>Here's a table:</p>
        <table>
            <tr>
                <th>Header 1</th>
                <th>Header 2</th>
            </tr>
            <tr>
                <td>Cell 1</td>
                <td>Cell 2</td>
            </tr>
        </table>
        <h3>Code Example</h3>
        <pre><code>def hello_world():
    print("Hello, World!")
        </code></pre>
    </body>
    </html>
    """


@pytest.fixture
def sample_crawl_result(sample_html):
    """Sample crawl result for testing"""
    return CrawlResult(
        url="https://example.com/test",
        html=sample_html,
        markdown="",  # Empty as we'll test the conversion
        links=["https://example.com/link1", "https://example.com/link2"],
        media=[{"url": "https://example.com/image.jpg", "type": "image"}],
        metadata={"source": "test"},
        success=True
    )


@pytest.mark.asyncio
async def test_initialization(content_processor):
    """Test content processor initialization"""
    assert not content_processor.is_initialized()
    await content_processor.initialize()
    assert content_processor.is_initialized()
    await content_processor.cleanup()


def test_convert_to_markdown(content_processor, sample_html):
    """Test HTML to markdown conversion"""
    markdown = content_processor.convert_to_markdown(sample_html)
    
    # Check that markdown contains expected elements
    assert "# Welcome to the Test Page" in markdown
    assert "**bold text**" in markdown
    assert "_italic text_" in markdown  # html2text uses underscores for italic
    assert "## Section 1" in markdown
    assert "* Item 1" in markdown
    assert "## Section 2" in markdown
    assert "Header 1" in markdown
    assert "Cell 1" in markdown
    assert "```" in markdown  # Code block


def test_extract_metadata(content_processor, sample_crawl_result):
    """Test metadata extraction"""
    metadata = content_processor.extract_metadata(sample_crawl_result)
    
    assert metadata['url'] == "https://example.com/test"
    assert metadata['title'] == "Test Page"
    assert 'timestamp' in metadata
    assert metadata['links_count'] == 2
    assert metadata['media_count'] == 1
    assert metadata['description'] == "This is a test page for content processing"
    assert metadata['keywords'] == ["test", "content", "processing"]
    assert 'content_quality_score' in metadata
    assert metadata['source'] == "test"  # From original metadata


def test_validate_content_quality(content_processor):
    """Test content quality validation"""
    # Test content that's too short
    short_content = "This is too short."
    assert not content_processor.validate_content_quality(short_content)
    
    # Test content with good length but poor quality (almost no text content)
    # Create content with lots of HTML but almost no actual text content
    poor_quality = "<html><head><title></title></head><body>" + "<div><span><p></p></span></div>" * 50 + "</body></html>"
    assert not content_processor.validate_content_quality(poor_quality)
    
    # Test good quality content
    good_content = """
    <html><body>
    <h1>Good Quality Content</h1>
    <p>This is a paragraph with meaningful content that should pass quality validation.</p>
    <p>It has multiple paragraphs and good structure.</p>
    <h2>Section with Details</h2>
    <p>More detailed content with proper sentences and structure.</p>
    <ul>
        <li>It has lists</li>
        <li>With multiple items</li>
    </ul>
    </body></html>
    """
    assert content_processor.validate_content_quality(good_content)


def test_detect_duplicates(content_processor):
    """Test duplicate content detection"""
    content1 = "<p>This is unique content for testing duplicate detection.</p>"
    content2 = "<div>This is unique content for testing duplicate detection.</div>"
    content3 = "<p>This is different content.</p>"
    
    # First occurrence should not be a duplicate
    assert not content_processor.detect_duplicates(content1)
    
    # Similar content with different HTML tags should be detected as duplicate
    assert content_processor.detect_duplicates(content2)
    
    # Different content should not be a duplicate
    assert not content_processor.detect_duplicates(content3)


def test_calculate_content_hash(content_processor):
    """Test content hash calculation"""
    content1 = "<p>Test content.</p>"
    content2 = "<div>Test content.</div>"
    content3 = "<p>Different content.</p>"
    
    # Similar content should have the same hash
    hash1 = content_processor.calculate_content_hash(content1)
    hash2 = content_processor.calculate_content_hash(content2)
    hash3 = content_processor.calculate_content_hash(content3)
    
    assert hash1 == hash2  # Same normalized content should have same hash
    assert hash1 != hash3  # Different content should have different hash


@patch('scraper.processors.content.detect')
def test_detect_language(mock_detect, content_processor):
    """Test language detection"""
    mock_detect.return_value = 'en'
    
    # Test English content
    english_content = "<p>This is English content for testing language detection.</p>"
    assert content_processor.detect_language(english_content) == 'en'
    
    # Test with exception
    mock_detect.side_effect = Exception("Test exception")
    assert content_processor.detect_language(english_content) == 'unknown'


def test_create_document(content_processor, sample_crawl_result):
    """Test document creation"""
    domains = ["agriculture", "water"]
    media_items = {
        "images": [
            {"url": "https://example.com/image.jpg", "type": "image"}
        ]
    }
    
    document = content_processor.create_document(sample_crawl_result, domains, media_items)
    
    assert document.url == sample_crawl_result.url
    assert document.title == "Test Page"
    assert document.content == sample_crawl_result.html
    assert document.markdown != ""  # Should have been converted
    assert document.domain_classifications == domains
    assert document.content_hash != ""
    assert len(document.media_catalog) == 1


def test_error_handling_in_conversion(content_processor):
    """Test error handling in HTML to markdown conversion"""
    # Create malformed HTML that might cause issues
    malformed_html = "<html><body><p>Unclosed paragraph tag<script>alert('test')"
    
    # The conversion should still work and not raise an exception
    markdown = content_processor.convert_to_markdown(malformed_html)
    assert "Unclosed paragraph tag" in markdown


def test_quality_score_calculation(content_processor):
    """Test quality score calculation with different content types"""
    # Empty content
    assert content_processor._calculate_quality_score("") == 0.0
    
    # Very simple content
    simple_content = "<p>Simple text.</p>"
    simple_score = content_processor._calculate_quality_score(simple_content)
    assert 0 < simple_score < 0.5  # Should be low but not zero
    
    # Complex content
    complex_content = """
    <html><body>
    <h1>Complex Content</h1>
    <p>This is a detailed paragraph with meaningful content.</p>
    <h2>Section 1</h2>
    <p>More detailed content with proper structure.</p>
    <ul>
        <li>Item 1 with details</li>
        <li>Item 2 with more information</li>
    </ul>
    <h2>Section 2</h2>
    <p>Another paragraph with useful information for testing.</p>
    <table>
        <tr><th>Header 1</th><th>Header 2</th></tr>
        <tr><td>Data 1</td><td>Data 2</td></tr>
    </table>
    </body></html>
    """
    complex_score = content_processor._calculate_quality_score(complex_content)
    assert complex_score > 0.5  # Should be higher
    
    # Compare scores
    assert complex_score > simple_score


def test_normalize_content_for_hashing(content_processor):
    """Test content normalization for hashing"""
    original = "<p>Test Content with UPPERCASE and punctuation!</p>"
    normalized = content_processor._normalize_content_for_hashing(original)
    
    assert normalized == "test content with uppercase and punctuation"
    assert "UPPERCASE" not in normalized
    assert "!" not in normalized


def test_post_process_markdown(content_processor):
    """Test markdown post-processing"""
    raw_markdown = """
    # Header
    
    
    
    Text with too many blank lines.
    
    ```
    
    ```
    
    ## Another header
    Text without proper spacing
    ### Subheader
    """
    
    processed = content_processor._post_process_markdown(raw_markdown)
    
    # Should not have more than 2 consecutive newlines
    assert "\n\n\n" not in processed
    
    # Should fix code block formatting
    assert "```\n```" in processed
    
    # Should add proper spacing around headers
    assert "Text without proper spacing\n\n    ### Subheader" in processed