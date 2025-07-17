"""
Media Extractor Implementation

Handles media extraction, file downloads, and organized storage
with resumable downloads and error recovery.
"""

import os
import re
import json
import asyncio
import aiohttp
import aiofiles
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path
import mimetypes
from datetime import datetime
import hashlib
from bs4 import BeautifulSoup

from scraper.core.base import (
    MediaExtractorInterface,
    CrawlResult,
    MediaItem,
    ProcessingError
)
from scraper.core.logging import get_logger


class MediaExtractor(MediaExtractorInterface):
    """
    Implementation of media extractor for identifying, cataloging,
    and downloading media files with organized storage and error recovery.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger()
        self.base_storage_path = config.get('files_path', './files')
        self.max_file_size = config.get('max_file_size', 100 * 1024 * 1024)  # 100MB
        self.download_timeout = config.get('download_timeout', 30)
        self.max_retries = config.get('max_download_retries', 3)
        self.retry_delay = config.get('retry_delay', 1.0)
        self.concurrent_downloads = config.get('concurrent_downloads', 5)
        
        # Supported file types
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'}
        self.document_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf'}
        self.archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
        self.video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'}
        self.audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'}
        
        # Create storage directories
        self._ensure_storage_directories()
    
    async def initialize(self) -> None:
        """Initialize the component"""
        self.logger.info("Initializing media extractor")
        self._ensure_storage_directories()
        self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Cleaning up media extractor")
    
    def _ensure_storage_directories(self) -> None:
        """Ensure storage directories exist"""
        base_path = Path(self.base_storage_path)
        
        # Create main directories
        directories = [
            'images',
            'documents', 
            'archives',
            'videos',
            'audio',
            'other'
        ]
        
        for directory in directories:
            (base_path / directory).mkdir(parents=True, exist_ok=True)
    
    def extract_media_urls(self, result: CrawlResult) -> Dict[str, List[MediaItem]]:
        """
        Extract media URLs from crawl result
        
        Args:
            result: Crawl result containing HTML and media data
            
        Returns:
            Dictionary of media items organized by type
        """
        self.logger.info(f"Extracting media URLs from {result.url}")
        
        media_items = {
            'images': [],
            'documents': [],
            'archives': [],
            'videos': [],
            'audio': [],
            'other': []
        }
        
        try:
            # Extract from crawl4ai media data first
            if result.media:
                for media_data in result.media:
                    media_item = self._create_media_item_from_crawl_data(media_data, result.url)
                    if media_item:
                        category = self._categorize_media_item(media_item)
                        media_items[category].append(media_item)
            
            # Extract additional media from HTML parsing
            if result.html:
                html_media_items = self._extract_media_from_html(result.html, result.url)
                for category, items in html_media_items.items():
                    # Avoid duplicates by checking URLs
                    existing_urls = {item.url for item in media_items[category]}
                    for item in items:
                        if item.url not in existing_urls:
                            media_items[category].append(item)
            
            # Log extraction results
            total_items = sum(len(items) for items in media_items.values())
            self.logger.info(f"Extracted {total_items} media items from {result.url}")
            
            for category, items in media_items.items():
                if items:
                    self.logger.debug(f"  {category}: {len(items)} items")
            
            return media_items
            
        except Exception as e:
            self.logger.error(f"Error extracting media URLs from {result.url}: {str(e)}")
            raise ProcessingError(f"Media extraction failed: {str(e)}")
    
    def _create_media_item_from_crawl_data(self, media_data: Dict[str, Any], base_url: str) -> Optional[MediaItem]:
        """
        Create MediaItem from crawl4ai media data
        
        Args:
            media_data: Media data from crawl4ai
            base_url: Base URL for resolving relative URLs
            
        Returns:
            MediaItem or None if invalid
        """
        try:
            url = media_data.get('url', '')
            if not url:
                return None
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, url)
            
            # Determine file type
            file_type = self._determine_file_type(absolute_url, media_data)
            
            return MediaItem(
                url=absolute_url,
                type=file_type,
                alt_text=media_data.get('alt', ''),
                file_size=media_data.get('size'),
                metadata={
                    'source_url': base_url,
                    'extraction_method': 'crawl4ai',
                    'original_data': media_data
                }
            )
        except Exception as e:
            self.logger.warning(f"Error creating media item from crawl data: {str(e)}")
            return None
    
    def _extract_media_from_html(self, html: str, base_url: str) -> Dict[str, List[MediaItem]]:
        """
        Extract media items from HTML content
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs
            
        Returns:
            Dictionary of media items by category
        """
        media_items = {
            'images': [],
            'documents': [],
            'archives': [],
            'videos': [],
            'audio': [],
            'other': []
        }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract images
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src')
                if src:
                    absolute_url = urljoin(base_url, src)
                    media_item = MediaItem(
                        url=absolute_url,
                        type='image',
                        alt_text=img.get('alt', ''),
                        metadata={
                            'source_url': base_url,
                            'extraction_method': 'html_parsing',
                            'tag': 'img',
                            'title': img.get('title', ''),
                            'width': img.get('width'),
                            'height': img.get('height')
                        }
                    )
                    media_items['images'].append(media_item)
            
            # Extract links to downloadable files
            link_tags = soup.find_all('a', href=True)
            for link in link_tags:
                href = link.get('href')
                if href:
                    absolute_url = urljoin(base_url, href)
                    file_type = self._determine_file_type(absolute_url)
                    
                    if file_type != 'other':  # Only include recognized file types
                        media_item = MediaItem(
                            url=absolute_url,
                            type=file_type,
                            alt_text=link.get_text(strip=True),
                            metadata={
                                'source_url': base_url,
                                'extraction_method': 'html_parsing',
                                'tag': 'a',
                                'link_text': link.get_text(strip=True),
                                'title': link.get('title', '')
                            }
                        )
                        category = self._categorize_media_item(media_item)
                        media_items[category].append(media_item)
            
            # Extract video sources
            video_tags = soup.find_all('video')
            for video in video_tags:
                src = video.get('src')
                if src:
                    absolute_url = urljoin(base_url, src)
                    media_item = MediaItem(
                        url=absolute_url,
                        type='video',
                        metadata={
                            'source_url': base_url,
                            'extraction_method': 'html_parsing',
                            'tag': 'video',
                            'controls': video.get('controls') is not None,
                            'autoplay': video.get('autoplay') is not None
                        }
                    )
                    media_items['videos'].append(media_item)
                
                # Check for source tags within video
                source_tags = video.find_all('source')
                for source in source_tags:
                    src = source.get('src')
                    if src:
                        absolute_url = urljoin(base_url, src)
                        media_item = MediaItem(
                            url=absolute_url,
                            type='video',
                            metadata={
                                'source_url': base_url,
                                'extraction_method': 'html_parsing',
                                'tag': 'source',
                                'media_type': source.get('type', '')
                            }
                        )
                        media_items['videos'].append(media_item)
            
            # Extract audio sources
            audio_tags = soup.find_all('audio')
            for audio in audio_tags:
                src = audio.get('src')
                if src:
                    absolute_url = urljoin(base_url, src)
                    media_item = MediaItem(
                        url=absolute_url,
                        type='audio',
                        metadata={
                            'source_url': base_url,
                            'extraction_method': 'html_parsing',
                            'tag': 'audio',
                            'controls': audio.get('controls') is not None,
                            'autoplay': audio.get('autoplay') is not None
                        }
                    )
                    media_items['audio'].append(media_item)
                
                # Check for source tags within audio
                source_tags = audio.find_all('source')
                for source in source_tags:
                    src = source.get('src')
                    if src:
                        absolute_url = urljoin(base_url, src)
                        media_item = MediaItem(
                            url=absolute_url,
                            type='audio',
                            metadata={
                                'source_url': base_url,
                                'extraction_method': 'html_parsing',
                                'tag': 'source',
                                'media_type': source.get('type', '')
                            }
                        )
                        media_items['audio'].append(media_item)
            
            return media_items
            
        except Exception as e:
            self.logger.warning(f"Error extracting media from HTML: {str(e)}")
            return media_items
    
    def _determine_file_type(self, url: str, media_data: Dict[str, Any] = None) -> str:
        """
        Determine file type from URL and optional media data
        
        Args:
            url: File URL
            media_data: Optional media data with type information
            
        Returns:
            File type string
        """
        # Check media data first if available
        if media_data and 'type' in media_data:
            media_type = media_data['type'].lower()
            if media_type.startswith('image/'):
                return 'image'
            elif media_type.startswith('video/'):
                return 'video'
            elif media_type.startswith('audio/'):
                return 'audio'
            elif media_type in ['application/pdf', 'application/msword', 'application/vnd.ms-excel']:
                return 'document'
            elif media_type in ['application/zip', 'application/x-rar-compressed']:
                return 'archive'
        
        # Fallback to URL extension
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path.lower())
        
        # Get file extension
        _, ext = os.path.splitext(path)
        
        if ext in self.image_extensions:
            return 'image'
        elif ext in self.document_extensions:
            return 'document'
        elif ext in self.archive_extensions:
            return 'archive'
        elif ext in self.video_extensions:
            return 'video'
        elif ext in self.audio_extensions:
            return 'audio'
        else:
            return 'other'
    
    def _categorize_media_item(self, media_item: MediaItem) -> str:
        """
        Categorize media item for storage organization
        
        Args:
            media_item: Media item to categorize
            
        Returns:
            Category string
        """
        if media_item.type == 'image':
            return 'images'
        elif media_item.type == 'document':
            return 'documents'
        elif media_item.type == 'archive':
            return 'archives'
        elif media_item.type == 'video':
            return 'videos'
        elif media_item.type == 'audio':
            return 'audio'
        else:
            return 'other'
    
    def create_media_catalog(self, media_data: Dict[str, List[MediaItem]]) -> str:
        """
        Create media catalog in markdown format
        
        Args:
            media_data: Dictionary of media items by category
            
        Returns:
            Markdown formatted catalog
        """
        self.logger.info("Creating media catalog")
        
        catalog_lines = [
            "# Media Catalog",
            "",
            f"Generated on: {datetime.now().isoformat()}",
            ""
        ]
        
        total_items = sum(len(items) for items in media_data.values())
        catalog_lines.extend([
            f"**Total Media Items:** {total_items}",
            ""
        ])
        
        for category, items in media_data.items():
            if not items:
                continue
            
            # Category header
            category_title = category.title()
            catalog_lines.extend([
                f"## {category_title} ({len(items)} items)",
                ""
            ])
            
            # Items table
            if category == 'images':
                catalog_lines.extend([
                    "| URL | Alt Text | Size | Status |",
                    "|-----|----------|------|--------|"
                ])
                for item in items:
                    size_str = f"{item.file_size} bytes" if item.file_size else "Unknown"
                    alt_text = (item.alt_text or "")[:50] + ("..." if len(item.alt_text or "") > 50 else "")
                    catalog_lines.append(f"| {item.url} | {alt_text} | {size_str} | {item.download_status} |")
            else:
                catalog_lines.extend([
                    "| URL | Description | Type | Size | Status |",
                    "|-----|-------------|------|------|--------|"
                ])
                for item in items:
                    size_str = f"{item.file_size} bytes" if item.file_size else "Unknown"
                    description = (item.alt_text or "")[:40] + ("..." if len(item.alt_text or "") > 40 else "")
                    catalog_lines.append(f"| {item.url} | {description} | {item.type} | {size_str} | {item.download_status} |")
            
            catalog_lines.append("")
        
        # Add metadata section
        catalog_lines.extend([
            "## Metadata",
            "",
            "### Download Statistics",
            ""
        ])
        
        for category, items in media_data.items():
            if items:
                downloaded = sum(1 for item in items if item.download_status == "completed")
                failed = sum(1 for item in items if item.download_status == "failed")
                pending = sum(1 for item in items if item.download_status == "pending")
                
                catalog_lines.extend([
                    f"**{category.title()}:**",
                    f"- Total: {len(items)}",
                    f"- Downloaded: {downloaded}",
                    f"- Failed: {failed}",
                    f"- Pending: {pending}",
                    ""
                ])
        
        return "\n".join(catalog_lines)
    
    async def download_files(self, media_items: List[MediaItem], destination: str) -> List[str]:
        """
        Download media files with resumable downloads and error recovery
        
        Args:
            media_items: List of media items to download
            destination: Destination directory
            
        Returns:
            List of successfully downloaded file paths
        """
        self.logger.info(f"Starting download of {len(media_items)} files to {destination}")
        
        # Ensure destination directory exists
        Path(destination).mkdir(parents=True, exist_ok=True)
        
        # Create semaphore for concurrent downloads
        semaphore = asyncio.Semaphore(self.concurrent_downloads)
        
        # Download files concurrently
        download_tasks = [
            self._download_single_file(item, destination, semaphore)
            for item in media_items
        ]
        
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # Process results
        successful_downloads = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Download failed for {media_items[i].url}: {str(result)}")
                media_items[i].download_status = "failed"
            elif result:
                successful_downloads.append(result)
                media_items[i].download_status = "completed"
                media_items[i].local_path = result
            else:
                media_items[i].download_status = "failed"
        
        self.logger.info(f"Downloaded {len(successful_downloads)} out of {len(media_items)} files")
        return successful_downloads
    
    async def _download_single_file(self, media_item: MediaItem, destination: str, semaphore: asyncio.Semaphore) -> Optional[str]:
        """
        Download a single file with retry logic
        
        Args:
            media_item: Media item to download
            destination: Destination directory
            semaphore: Semaphore for concurrency control
            
        Returns:
            Local file path if successful, None otherwise
        """
        async with semaphore:
            for attempt in range(self.max_retries + 1):
                try:
                    return await self._attempt_download(media_item, destination)
                except Exception as e:
                    self.logger.warning(f"Download attempt {attempt + 1} failed for {media_item.url}: {str(e)}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                    else:
                        self.logger.error(f"All download attempts failed for {media_item.url}")
                        return None
    
    async def _attempt_download(self, media_item: MediaItem, destination: str) -> str:
        """
        Attempt to download a single file
        
        Args:
            media_item: Media item to download
            destination: Destination directory
            
        Returns:
            Local file path
        """
        # Generate filename
        filename = self._generate_filename(media_item.url)
        filepath = Path(destination) / filename
        
        # Check if file already exists and is complete
        if filepath.exists():
            existing_size = filepath.stat().st_size
            if media_item.file_size and existing_size == media_item.file_size:
                self.logger.debug(f"File already exists and is complete: {filepath}")
                return str(filepath)
        
        # Download file
        timeout = aiohttp.ClientTimeout(total=self.download_timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {}
            
            # Support resumable downloads
            if filepath.exists():
                existing_size = filepath.stat().st_size
                headers['Range'] = f'bytes={existing_size}-'
                mode = 'ab'  # Append mode
            else:
                mode = 'wb'  # Write mode
            
            async with session.get(media_item.url, headers=headers) as response:
                # Check response status
                if response.status not in [200, 206]:  # 206 for partial content
                    raise ProcessingError(f"HTTP {response.status} for {media_item.url}")
                
                # Get file size from headers
                content_length = response.headers.get('content-length')
                if content_length:
                    file_size = int(content_length)
                    if mode == 'ab':
                        file_size += filepath.stat().st_size
                    
                    # Check file size limit
                    if file_size > self.max_file_size:
                        raise ProcessingError(f"File too large: {file_size} bytes (max: {self.max_file_size})")
                    
                    # Update media item with file size
                    if not media_item.file_size:
                        media_item.file_size = file_size
                
                # Download file
                async with aiofiles.open(filepath, mode) as f:
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Check size limit during download
                        if downloaded > self.max_file_size:
                            filepath.unlink(missing_ok=True)  # Delete partial file
                            raise ProcessingError(f"File too large during download: {downloaded} bytes")
        
        # Verify download
        if not filepath.exists():
            raise ProcessingError("File was not created")
        
        final_size = filepath.stat().st_size
        if media_item.file_size and final_size != media_item.file_size:
            self.logger.warning(f"File size mismatch for {media_item.url}: expected {media_item.file_size}, got {final_size}")
        
        self.logger.debug(f"Successfully downloaded: {filepath} ({final_size} bytes)")
        return str(filepath)
    
    def _generate_filename(self, url: str) -> str:
        """
        Generate a safe filename from URL
        
        Args:
            url: File URL
            
        Returns:
            Safe filename
        """
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        
        # Get filename from path
        filename = os.path.basename(path)
        
        # If no filename, generate one from URL hash
        if not filename or '.' not in filename:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            
            # Try to determine extension from URL or content type
            _, ext = os.path.splitext(path)
            if not ext:
                ext = '.bin'  # Default extension
            
            filename = f"file_{url_hash}{ext}"
        
        # Sanitize filename
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename[:255]  # Limit filename length
        
        return filename
    
    def organize_files(self, files: List[str], source_domain: str) -> None:
        """
        Organize downloaded files by domain and file type
        
        Args:
            files: List of downloaded file paths
            source_domain: Source domain for organization
        """
        self.logger.info(f"Organizing {len(files)} files for domain {source_domain}")
        
        try:
            # Create domain directory
            domain_dir = Path(self.base_storage_path) / source_domain
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            # Create type directories within domain
            type_dirs = {
                'images': domain_dir / 'images',
                'documents': domain_dir / 'documents',
                'archives': domain_dir / 'archives',
                'videos': domain_dir / 'videos',
                'audio': domain_dir / 'audio',
                'other': domain_dir / 'other'
            }
            
            for type_dir in type_dirs.values():
                type_dir.mkdir(parents=True, exist_ok=True)
            
            # Move files to appropriate directories
            for file_path in files:
                try:
                    source_path = Path(file_path)
                    if not source_path.exists():
                        continue
                    
                    # Determine file type
                    file_type = self._determine_file_type(str(source_path))
                    
                    # Determine target directory
                    if file_type == 'image':
                        target_dir = type_dirs['images']
                    elif file_type == 'document':
                        target_dir = type_dirs['documents']
                    elif file_type == 'archive':
                        target_dir = type_dirs['archives']
                    elif file_type == 'video':
                        target_dir = type_dirs['videos']
                    elif file_type == 'audio':
                        target_dir = type_dirs['audio']
                    else:
                        target_dir = type_dirs['other']
                    
                    # Move file
                    target_path = target_dir / source_path.name
                    
                    # Handle filename conflicts
                    counter = 1
                    original_target = target_path
                    while target_path.exists():
                        stem = original_target.stem
                        suffix = original_target.suffix
                        target_path = target_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    source_path.rename(target_path)
                    self.logger.debug(f"Moved {source_path} to {target_path}")
                    
                except Exception as e:
                    self.logger.error(f"Error organizing file {file_path}: {str(e)}")
            
            self.logger.info(f"Successfully organized files for domain {source_domain}")
            
        except Exception as e:
            self.logger.error(f"Error organizing files for domain {source_domain}: {str(e)}")
            raise ProcessingError(f"File organization failed: {str(e)}")