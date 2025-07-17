"""
Command Line Interface for Production Web Scraper

This package provides command line argument parsing and validation
for the web scraper application. It handles mode selection, URL input
options, and configuration overrides.

Classes:
    CLIManager: Command line interface manager for the scraper
"""

from scraper.cli.arguments import CLIManager

__all__ = ['CLIManager']