"""
Command Line Argument Parsing for Production Web Scraper

Handles command line arguments for mode selection, URL input options,
and configuration overrides.
"""

import argparse
import os
import sys
import json
import csv
from pathlib import Path
from typing import List, Optional, Dict, Any


class CLIManager:
    """
    Command line interface manager for the scraper
    
    Handles command line arguments for mode selection, URL input options,
    and configuration overrides. Provides validation and help documentation.
    """
    
    def __init__(self):
        self.parser = self._create_parser()
        self._default_urls = [
            "https://pac.com.pk/",
            "https://ztbl.com.pk/",
            "https://ffc.com.pk/kashtkar-desk/",
            "https://aari.punjab.gov.pk/",
            "https://plantprotection.gov.pk/",
            "https://web.uaf.edu.pk/",
            "https://namc.pmd.gov.pk/",
            "https://www.parc.gov.pk/",
            "http://www.amis.pk/",
            "https://agripunjab.gov.pk/",
            "https://www.fao.org/home/en",
            "https://www.pcrwr.gov.pk",
            "https://nwfc.pmd.gov.pk/new/daily-forecast.php",
            "https://www.pmd.gov.pk/en/",
            "https://www.iwmi.org/",
            "https://www.cgiar.org/"
        ]
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Create argument parser with all options
        
        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            description="Production Web Scraper for RAG content generation",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            epilog=self._get_epilog()
        )
        
        # Mode selection
        parser.add_argument(
            "--mode",
            choices=["dev", "prod"],
            default="dev",
            help="Processing mode: development (local storage) or production (RAG API)"
        )
        
        # URL input options
        url_group = parser.add_argument_group("URL Sources")
        url_source = url_group.add_mutually_exclusive_group()
        url_source.add_argument(
            "--urls",
            nargs="+",
            help="One or more URLs to process"
        )
        url_source.add_argument(
            "--url-file",
            help="Path to file containing URLs (supports TXT, CSV, JSON formats)"
        )
        url_source.add_argument(
            "--use-default-urls",
            action="store_true",
            help="Use the default list of agricultural websites"
        )
        
        # Configuration options
        config_group = parser.add_argument_group("Configuration")
        config_group.add_argument(
            "--config",
            default="config/config.yaml",
            help="Path to configuration file"
        )
        config_group.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Logging level"
        )
        config_group.add_argument(
            "--max-workers",
            type=int,
            help="Maximum number of concurrent workers"
        )
        config_group.add_argument(
            "--max-depth",
            type=int,
            help="Maximum crawl depth for following links"
        )
        config_group.add_argument(
            "--rate-limit",
            type=float,
            help="Rate limit in seconds between requests to the same domain"
        )
        
        # Advanced options
        advanced_group = parser.add_argument_group("Advanced Options")
        advanced_group.add_argument(
            "--timeout",
            type=int,
            help="Request timeout in seconds"
        )
        advanced_group.add_argument(
            "--no-js",
            action="store_true",
            help="Disable JavaScript execution during crawling"
        )
        advanced_group.add_argument(
            "--no-images",
            action="store_true",
            help="Skip waiting for images during crawling"
        )
        advanced_group.add_argument(
            "--no-downloads",
            action="store_true",
            help="Disable file downloads"
        )
        
        # Version and examples
        parser.add_argument(
            "--version",
            action="version",
            version="Production Web Scraper v0.1.0"
        )
        
        parser.add_argument(
            "--examples",
            action="store_true",
            help="Show usage examples and exit"
        )
        
        return parser
    
    def _get_epilog(self) -> str:
        """
        Get epilog text for help message
        
        Returns:
            Formatted epilog text
        """
        return """
Examples:
  # Run in development mode with default URLs
  python -m scraper

  # Run in production mode with specific URLs
  python -m scraper --mode=prod --urls https://example.com https://example.org

  # Run with URLs from a file
  python -m scraper --url-file=my_urls.txt

  # Run with custom configuration
  python -m scraper --config=my_config.yaml --max-workers=5 --max-depth=2

  # Run with advanced options
  python -m scraper --timeout=60 --no-js --no-images

Notes:
  - Development mode saves content to local folders in ./docs/
  - Production mode requires RAG_API_KEY environment variable
  - Default URLs are agricultural websites if no URLs are provided
  - URL files can be TXT (one URL per line), CSV, or JSON format
"""
    
    def parse_arguments(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """
        Parse command line arguments
        
        Args:
            args: Command line arguments (uses sys.argv if None)
            
        Returns:
            Parsed arguments namespace
        """
        parsed_args = self.parser.parse_args(args)
        self.validate_arguments(parsed_args)
        return parsed_args
    
    def validate_arguments(self, args: argparse.Namespace) -> bool:
        """
        Validate parsed arguments for consistency
        
        Args:
            args: Parsed arguments namespace
            
        Returns:
            True if arguments are valid
            
        Raises:
            ValueError: If arguments are invalid
        """
        # Production mode requires API key
        if args.mode == "prod":
            if not os.getenv("RAG_API_KEY"):
                self.parser.error("Production mode requires RAG_API_KEY environment variable")
        
        # Check URL file exists and is readable
        if args.url_file and not Path(args.url_file).is_file():
            self.parser.error(f"URL file not found: {args.url_file}")
        
        # Check config file exists
        if not Path(args.config).is_file():
            self.parser.error(f"Configuration file not found: {args.config}")
        
        # Validate numeric arguments
        if args.max_workers is not None and args.max_workers <= 0:
            self.parser.error("Maximum workers must be greater than 0")
        
        if args.max_depth is not None and args.max_depth < 0:
            self.parser.error("Maximum depth must be non-negative")
        
        if args.rate_limit is not None and args.rate_limit < 0:
            self.parser.error("Rate limit must be non-negative")
        
        if args.timeout is not None and args.timeout <= 0:
            self.parser.error("Timeout must be greater than 0")
        
        return True
    
    def get_urls_from_args(self, args: argparse.Namespace) -> List[str]:
        """
        Get URLs from command line arguments or default list
        
        Args:
            args: Parsed arguments namespace
            
        Returns:
            List of URLs to process
        """
        # Direct URL arguments
        if args.urls:
            return args.urls
        
        # URL file
        if args.url_file:
            return self._load_urls_from_file(args.url_file)
        
        # Use default URLs if explicitly requested or no other URLs provided
        if args.use_default_urls or (not args.urls and not args.url_file):
            return self.get_default_urls()
        
        return []
    
    def _load_urls_from_file(self, file_path: str) -> List[str]:
        """
        Load URLs from file in various formats
        
        Args:
            file_path: Path to file containing URLs
            
        Returns:
            List of URLs
            
        Raises:
            ValueError: If file format is not supported or file is invalid
        """
        file_path = Path(file_path)
        urls = []
        
        try:
            # Try to determine file type from extension
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        urls = [str(url) for url in data if url]
                    elif isinstance(data, dict) and 'urls' in data:
                        urls = [str(url) for url in data['urls'] if url]
                    else:
                        raise ValueError(f"Invalid JSON format in {file_path}")
            
            elif file_path.suffix.lower() == '.csv':
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0].strip():
                            urls.append(row[0].strip())
            
            else:  # Default to text file with one URL per line
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
        
        except Exception as e:
            raise ValueError(f"Failed to load URLs from {file_path}: {e}")
        
        if not urls:
            raise ValueError(f"No valid URLs found in {file_path}")
        
        return urls
    
    def get_default_urls(self) -> List[str]:
        """
        Get default list of agricultural websites
        
        Returns:
            List of default URLs
        """
        return self._default_urls
    
    def print_help(self) -> None:
        """Print help message"""
        self.parser.print_help()
    
    def get_usage_examples(self) -> str:
        """
        Get usage examples for documentation
        
        Returns:
            Formatted usage examples
        """
        return self._get_epilog()
    
    def print_default_urls(self) -> None:
        """
        Print the list of default URLs
        """
        print("\nDefault URLs:")
        for i, url in enumerate(self._default_urls, 1):
            print(f"{i}. {url}")