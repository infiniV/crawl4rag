"""
Content Processor Implementation

Handles HTML to markdown conversion, content quality validation,
duplicate detection, and metadata extraction.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import re
import html2text
from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException

from scraper.core.base import (
    ContentProcessorInterface,
    CrawlResult,
    ScrapedDocument,
    MediaItem,
    ProcessingError
)
from scraper.core.logging import get_logger


class ContentProcessor(ContentProcessorInterface):
    """
    Implementation of content processor for converting HTML to markdown,
    validating content quality, detecting duplicates, and handling language detection.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger()
        self.min_content_length = config.get('min_content_length', 100)
        self.min_content_quality_score = config.get('min_content_quality_score', 0.3)
        self.content_hashes = set()
        
        # Configure HTML to Markdown converter
        self.html2text_config = {
            'unicode_snob': True,
            'body_width': 0,  # No wrapping
            'protect_links': True,
            'ignore_images': False,
            'ignore_tables': False,
            'ignore_emphasis': False,
            'bypass_tables': False,
            'escape_snob': False,
            'images_to_alt': False,
            'images_with_size': True,
            'reference_links': False,
            'default_image_alt': '',
            'mark_code': True  # Enable code block detection
        }
        
        # Initialize HTML to Markdown converter
        self.h2t = html2text.HTML2Text()
        for key, value in self.html2text_config.items():
            if hasattr(self.h2t, key):
                setattr(self.h2t, key, value)
    
    async def initialize(self) -> None:
        """Initialize the component"""
        self.logger.info("Initializing content processor")
        self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Cleaning up content processor")
    
    def convert_to_markdown(self, html: str) -> str:
        """
        Convert HTML to markdown preserving structure and formatting
        
        Args:
            html: HTML content
            
        Returns:
            Markdown content
        """
        self.logger.info("Converting HTML to markdown")
        
        try:
            # Clean HTML first using BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "iframe", "noscript"]):
                script.decompose()
            
            # Handle code blocks specially before conversion
            self._prepare_code_blocks(soup)
            
            # Convert to markdown using html2text
            markdown = self.h2t.handle(str(soup))
            
            # Post-process markdown for better formatting
            markdown = self._post_process_markdown(markdown)
            
            return markdown
        except Exception as e:
            self.logger.error(f"Error converting HTML to markdown: {str(e)}")
            raise ProcessingError(f"HTML to markdown conversion failed: {str(e)}")
    
    def _prepare_code_blocks(self, soup: BeautifulSoup) -> None:
        """
        Prepare code blocks for better markdown conversion
        
        Args:
            soup: BeautifulSoup object to process
        """
        # Find all code and pre elements
        code_elements = soup.find_all(['code', 'pre'])
        
        for element in code_elements:
            # Add markers to preserve code formatting
            if element.name == 'pre':
                # Wrap pre elements to preserve as code blocks
                element.insert(0, soup.new_string('\n```\n'))
                element.append(soup.new_string('\n```\n'))
            elif element.name == 'code' and element.parent.name != 'pre':
                # Inline code elements
                element.insert(0, soup.new_string('`'))
                element.append(soup.new_string('`'))
    
    def _post_process_markdown(self, markdown: str) -> str:
        """
        Post-process markdown for better formatting
        
        Args:
            markdown: Raw markdown content
            
        Returns:
            Processed markdown content
        """
        # Fix multiple consecutive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Fix code blocks formatting - handle empty code blocks
        markdown = re.sub(r'```\s*\n\s*```', '```\n```', markdown)
        
        # Ensure proper spacing around headers - more precise pattern
        markdown = re.sub(r'([^\n])\n(\s*#{1,6} )', r'\1\n\n\2', markdown)
        
        # Fix table formatting if needed
        markdown = re.sub(r'\|\s*\n\s*\|', '|\n|', markdown)
        
        return markdown
    
    def extract_metadata(self, result: CrawlResult) -> Dict[str, Any]:
        """
        Extract metadata from crawl result
        
        Args:
            result: Crawl result
            
        Returns:
            Metadata dictionary
        """
        # Extract basic metadata
        metadata = {
            'url': result.url,
            'title': self._extract_title(result.html),
            'timestamp': datetime.now().isoformat(),
            'links_count': len(result.links),
            'media_count': len(result.media)
        }
        
        # Detect language
        try:
            language = self.detect_language(result.html)
            if language:
                metadata['language'] = language
        except Exception as e:
            self.logger.warning(f"Language detection failed: {str(e)}")
            metadata['language'] = 'unknown'
        
        # Extract meta description
        description = self._extract_meta_description(result.html)
        if description:
            metadata['description'] = description
        
        # Extract meta keywords
        keywords = self._extract_meta_keywords(result.html)
        if keywords:
            metadata['keywords'] = keywords
        
        # Add content quality score
        metadata['content_quality_score'] = self._calculate_quality_score(result.html)
        
        # Add any metadata from the crawl result
        if result.metadata:
            metadata.update(result.metadata)
        
        return metadata
    
    def _extract_title(self, html: str) -> str:
        """
        Extract title from HTML
        
        Args:
            html: HTML content
            
        Returns:
            Page title
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                return title_tag.string.strip()
            
            # Fallback to h1 if no title tag
            h1_tag = soup.find('h1')
            if h1_tag and h1_tag.string:
                return h1_tag.string.strip()
        except Exception as e:
            self.logger.warning(f"Error extracting title: {str(e)}")
        
        return "Untitled Document"
    
    def _extract_meta_description(self, html: str) -> Optional[str]:
        """
        Extract meta description from HTML
        
        Args:
            html: HTML content
            
        Returns:
            Meta description or None
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                return meta_desc['content'].strip()
            
            # Try Open Graph description
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                return og_desc['content'].strip()
        except Exception as e:
            self.logger.warning(f"Error extracting meta description: {str(e)}")
        
        return None
    
    def _extract_meta_keywords(self, html: str) -> Optional[List[str]]:
        """
        Extract meta keywords from HTML
        
        Args:
            html: HTML content
            
        Returns:
            List of keywords or None
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and meta_keywords.get('content'):
                keywords = [k.strip() for k in meta_keywords['content'].split(',')]
                return [k for k in keywords if k]  # Filter empty strings
        except Exception as e:
            self.logger.warning(f"Error extracting meta keywords: {str(e)}")
        
        return None
    
    def validate_content_quality(self, content: str) -> bool:
        """
        Validate content quality based on length and quality score
        
        Args:
            content: Content to validate
            
        Returns:
            True if content meets quality standards
        """
        # Check content length
        if len(content) < self.min_content_length:
            self.logger.warning(f"Content too short: {len(content)} characters")
            return False
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(content)
        
        # Check quality score
        if quality_score < self.min_content_quality_score:
            self.logger.warning(f"Content quality too low: {quality_score:.2f}")
            return False
        
        return True
    
    def _calculate_quality_score(self, content: str) -> float:
        """
        Calculate content quality score based on various metrics
        
        Args:
            content: Content to evaluate
            
        Returns:
            Quality score between 0 and 1
        """
        try:
            # Use BeautifulSoup to extract text
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            
            # Skip empty content
            if not text:
                return 0.0
            
            # Calculate metrics
            total_chars = len(text)
            if total_chars == 0:
                return 0.0
                
            # Text to HTML ratio (higher is better)
            html_size = len(content)
            text_ratio = total_chars / max(html_size, 1)
            
            # Word count (higher is better)
            words = text.split()
            word_count = len(words)
            
            # Average word length (higher can indicate more complex content)
            avg_word_length = sum(len(word) for word in words) / max(word_count, 1)
            
            # Sentence count (higher is better)
            sentences = re.split(r'[.!?]+', text)
            sentence_count = len([s for s in sentences if s.strip()])
            
            # Paragraph count from HTML (higher is better)
            paragraph_count = len(soup.find_all('p'))
            
            # Heading count (indicates structure)
            heading_count = len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
            
            # Calculate composite score (weights can be adjusted)
            score = 0.0
            
            # Text ratio component (0-0.25)
            score += min(text_ratio * 5, 0.25)  # Cap at 0.25
            
            # Word count component (0-0.25)
            score += min(word_count / 500, 0.25)  # Cap at 0.25 for 500+ words
            
            # Structure component (0-0.25)
            structure_score = min((paragraph_count / 5) * 0.15, 0.15)  # Cap at 0.15 for 5+ paragraphs
            structure_score += min((heading_count / 3) * 0.1, 0.1)  # Cap at 0.1 for 3+ headings
            score += structure_score
            
            # Sentence complexity component (0-0.25)
            if sentence_count > 0:
                avg_sentence_length = word_count / sentence_count
                sentence_score = min(avg_sentence_length / 20, 0.25)  # Cap at 0.25
                score += sentence_score
            
            return min(score, 1.0)  # Ensure score is between 0 and 1
            
        except Exception as e:
            self.logger.warning(f"Error calculating quality score: {str(e)}")
            return 0.0
    
    def detect_duplicates(self, content: str) -> bool:
        """
        Detect duplicate content using content hashing
        
        Args:
            content: Content to check for duplicates
            
        Returns:
            True if content is a duplicate
        """
        content_hash = self.calculate_content_hash(content)
        
        if content_hash in self.content_hashes:
            self.logger.warning(f"Duplicate content detected with hash: {content_hash}")
            return True
        
        self.content_hashes.add(content_hash)
        return False
    
    def calculate_content_hash(self, content: str) -> str:
        """
        Calculate content hash for deduplication using normalized content
        
        Args:
            content: Content to hash
            
        Returns:
            Content hash
        """
        # Normalize content before hashing to improve duplicate detection
        normalized_content = self._normalize_content_for_hashing(content)
        return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()
    
    def _normalize_content_for_hashing(self, content: str) -> str:
        """
        Normalize content for more effective duplicate detection
        
        Args:
            content: Content to normalize
            
        Returns:
            Normalized content
        """
        # If it's HTML, extract text
        if '<html' in content.lower() or '<body' in content.lower() or '<p>' in content.lower() or '<div>' in content.lower():
            try:
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text(separator=' ', strip=True)
            except Exception:
                pass
        
        # Convert to lowercase
        content = content.lower()
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Remove punctuation
        content = re.sub(r'[^\w\s]', '', content)
        
        return content
    
    def detect_language(self, content: str) -> str:
        """
        Detect language of content
        
        Args:
            content: Content to analyze
            
        Returns:
            ISO 639-1 language code
        """
        try:
            # Extract text if HTML
            if '<html' in content.lower() or '<body' in content.lower():
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
            else:
                text = content
            
            # Skip short texts
            if len(text) < 50:
                return 'unknown'
            
            # Detect language
            return detect(text)
        except LangDetectException:
            return 'unknown'
        except Exception as e:
            self.logger.warning(f"Language detection error: {str(e)}")
            return 'unknown'
    
    def create_document(self, result: CrawlResult, domains: List[str], 
                       media_items: Dict[str, List[MediaItem]]) -> ScrapedDocument:
        """
        Create document from crawl result
        
        Args:
            result: Crawl result
            domains: Domain classifications
            media_items: Media items by type
            
        Returns:
            Scraped document
        """
        metadata = self.extract_metadata(result)
        
        # Convert HTML to markdown if not already done
        markdown = result.markdown
        if not markdown and result.html:
            markdown = self.convert_to_markdown(result.html)
        
        content_hash = self.calculate_content_hash(markdown or result.html)
        
        return ScrapedDocument(
            url=result.url,
            title=metadata.get('title', 'Untitled Document'),
            content=result.html,
            markdown=markdown,
            metadata=metadata,
            media_catalog=list(media_items.values()) if media_items else [],
            domain_classifications=domains,
            timestamp=datetime.now(),
            content_hash=content_hash
        )