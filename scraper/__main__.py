#!/usr/bin/env python3
"""
Production Web Scraper - Main Entry Point

This module serves as the main entry point for the web scraper application.
It initializes the configuration, sets up logging, and starts the scraping process.
"""

import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path to allow running as script
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from scraper.core.config import ConfigManager
from scraper.core.logging import setup_logging, get_logger
from scraper.core.base import ProcessingMode
from scraper.cli.arguments import CLIManager
from scraper.core.orchestrator import ScraperOrchestratorImpl
from scraper.utils.component_factory import create_and_register_components


async def main() -> int:
    """Main entry point for the scraper"""
    # Parse command line arguments
    cli_manager = CLIManager()
    args = cli_manager.parse_arguments()
    
    # Handle special flags
    if args.examples:
        print("\nProduction Web Scraper - Usage Examples\n")
        print(cli_manager.get_usage_examples())
        return 0
        
    # Show default URLs if requested with --use-default-urls and --urls/--url-file not provided
    if args.use_default_urls and not (args.urls or args.url_file):
        print("\nUsing default URLs:")
        cli_manager.print_default_urls()
        print("")
    
    # Load configuration
    config_manager = ConfigManager(args.config)
    config = config_manager.load_config()
    
    # Set up logging
    logging_config = config_manager.logging_config
    setup_logging(
        level=args.log_level or logging_config.level,
        log_file=logging_config.file,
        max_size=logging_config.max_size,
        backup_count=logging_config.backup_count
    )
    logger = get_logger()
    
    # Determine processing mode
    mode_str = args.mode
    mode = ProcessingMode.PRODUCTION if mode_str.lower() == 'prod' else ProcessingMode.DEVELOPMENT
    logger.info(f"Running in {mode_str.upper()} mode")
    
    # Update the config with the mode from command line
    config_manager.scraper_config.mode = mode_str.lower()
    
    # Update the config dictionary directly
    if 'scraper' not in config:
        config['scraper'] = {}
    config['scraper']['mode'] = mode_str.lower()
    
    # Validate configuration for selected mode
    try:
        config_manager.validate_config(mode_str)
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return 1
    
    # Get URLs to process
    try:
        urls = cli_manager.get_urls_from_args(args)
        if not urls:
            logger.error("No URLs to process. Use --urls, --url-file, or --use-default-urls")
            cli_manager.print_help()
            return 1
        
        logger.info(f"Processing {len(urls)} URLs")
    except Exception as e:
        logger.error(f"Failed to get URLs: {e}")
        return 1
        
    # Apply command line overrides to configuration
    if args.max_workers is not None:
        config_manager.scraper_config.max_workers = args.max_workers
        
    if args.max_depth is not None:
        config_manager.scraper_config.max_depth = args.max_depth
        
    if args.rate_limit is not None:
        config_manager.scraper_config.rate_limit = args.rate_limit
        
    if args.timeout is not None:
        config_manager.scraper_config.timeout = args.timeout
        
    # Apply advanced options
    if args.no_js:
        config_manager.crawl_config.headless = True
        
    if args.no_images:
        config_manager.crawl_config.wait_for_images = False
        
    if args.no_downloads:
        config_manager.crawl_config.accept_downloads = False
    
    # Initialize and run the scraper
    try:
        orchestrator = ScraperOrchestratorImpl(config)
        # Create and register components
        create_and_register_components(orchestrator, config)
        await orchestrator.initialize()
        results = await orchestrator.process_urls(urls, mode)
        await orchestrator.cleanup()
        
        # Log summary
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Processing completed: {success_count}/{len(results)} URLs successful")
        
        return 0 if success_count > 0 else 1
    except Exception as e:
        logger.error(f"Scraper execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nScraper interrupted by user")
        sys.exit(130)