"""
Logging System for Production Web Scraper

Provides comprehensive logging with file rotation, different log levels,
and structured logging for monitoring and debugging.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json


class LoggingManager:
    """
    Centralized logging manager with file rotation and structured logging
    """
    
    def __init__(self):
        self.logger: Optional[logging.Logger] = None
        self.file_handler: Optional[logging.handlers.RotatingFileHandler] = None
        self.console_handler: Optional[logging.StreamHandler] = None
        self._setup_complete = False
    
    def setup_logging(self, level: str = "INFO", log_file: str = "./logs/scraper.log", 
                     max_size: str = "100MB", backup_count: int = 5) -> None:
        """
        Set up logging system with file rotation and console output
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file
            max_size: Maximum size before rotation (e.g., "100MB")
            backup_count: Number of backup files to keep
        """
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert max_size string to bytes
        max_bytes = self._parse_size(max_size)
        
        # Create logger
        self.logger = logging.getLogger('scraper')
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File handler with rotation
        self.file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
        )
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(self.file_handler)
        
        # Console handler
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(getattr(logging, level.upper()))
        self.console_handler.setFormatter(console_formatter)
        self.logger.addHandler(self.console_handler)
        
        self._setup_complete = True
        self.logger.info("Logging system initialized")
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '100MB' to bytes"""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            # Assume bytes
            return int(size_str)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        if not self._setup_complete or not self.logger:
            raise RuntimeError("Logging not set up. Call setup_logging() first.")
        return self.logger
    
    def log_processing_start(self, urls: list, mode: str) -> None:
        """Log the start of processing with context"""
        if not self.logger:
            return
            
        self.logger.info(f"Starting scraper in {mode} mode")
        self.logger.info(f"Processing {len(urls)} URLs")
        self.logger.debug(f"URLs to process: {urls}")
    
    def log_url_result(self, url: str, success: bool, processing_time: float, 
                      error_message: Optional[str] = None) -> None:
        """Log the result of processing a single URL"""
        if not self.logger:
            return
            
        if success:
            self.logger.info(f"Successfully processed {url} in {processing_time:.2f}s")
        else:
            self.logger.error(f"Failed to process {url} after {processing_time:.2f}s: {error_message}")
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error with context information"""
        if not self.logger:
            return
            
        context_str = ""
        if context:
            context_str = f" | Context: {json.dumps(context, default=str)}"
        
        self.logger.error(f"Error: {str(error)}{context_str}", exc_info=True)
    
    def log_warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning with optional context"""
        if not self.logger:
            return
            
        context_str = ""
        if context:
            context_str = f" | Context: {json.dumps(context, default=str)}"
        
        self.logger.warning(f"{message}{context_str}")
    
    def log_progress(self, current: int, total: int, message: str = "") -> None:
        """Log progress information"""
        if not self.logger:
            return
            
        percentage = (current / total) * 100 if total > 0 else 0
        progress_msg = f"Progress: {current}/{total} ({percentage:.1f}%)"
        if message:
            progress_msg += f" - {message}"
        
        self.logger.info(progress_msg)
    
    def generate_summary_report(self, stats: Dict[str, Any]) -> str:
        """Generate and log a comprehensive summary report"""
        if not self.logger:
            return ""
        
        report_lines = [
            "=" * 60,
            "SCRAPING SESSION SUMMARY",
            "=" * 60,
            f"Start Time: {stats.get('start_time', 'Unknown')}",
            f"End Time: {stats.get('end_time', 'Unknown')}",
            f"Total Duration: {stats.get('duration', 'Unknown')}",
            f"Mode: {stats.get('mode', 'Unknown')}",
            "",
            "URL PROCESSING:",
            f"  Total URLs: {stats.get('total_urls', 0)}",
            f"  Successful: {stats.get('successful_urls', 0)}",
            f"  Failed: {stats.get('failed_urls', 0)}",
            f"  Success Rate: {stats.get('success_rate', 0):.1f}%",
            "",
            "CONTENT PROCESSING:",
            f"  Documents Created: {stats.get('documents_created', 0)}",
            f"  Media Files Found: {stats.get('media_files_found', 0)}",
            f"  Files Downloaded: {stats.get('files_downloaded', 0)}",
            f"  Total Content Size: {stats.get('total_content_size', 'Unknown')}",
            "",
            "DOMAIN CLASSIFICATION:",
        ]
        
        # Add domain statistics
        domain_stats = stats.get('domain_stats', {})
        for domain, count in domain_stats.items():
            report_lines.append(f"  {domain.capitalize()}: {count} documents")
        
        if stats.get('errors'):
            report_lines.extend([
                "",
                "ERRORS ENCOUNTERED:",
            ])
            for error in stats.get('errors', [])[:10]:  # Show first 10 errors
                report_lines.append(f"  - {error}")
            
            if len(stats.get('errors', [])) > 10:
                report_lines.append(f"  ... and {len(stats.get('errors', [])) - 10} more errors")
        
        report_lines.append("=" * 60)
        
        report = "\n".join(report_lines)
        self.logger.info(f"Session Summary:\n{report}")
        
        return report
    
    def close(self) -> None:
        """Close logging handlers"""
        if self.file_handler:
            self.file_handler.close()
        if self.console_handler:
            self.console_handler.close()


# Global logging manager instance
logging_manager = LoggingManager()


def get_logger() -> logging.Logger:
    """Get the global logger instance"""
    return logging_manager.get_logger()


def setup_logging(level: str = "INFO", log_file: str = "./logs/scraper.log", 
                 max_size: str = "100MB", backup_count: int = 5) -> None:
    """Set up global logging system"""
    logging_manager.setup_logging(level, log_file, max_size, backup_count)