#!/usr/bin/env python3
"""
Test script for CLI functionality

This script tests the command line interface functionality
by simulating different command line arguments and verifying
the behavior.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to allow running as script
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from scraper.cli.arguments import CLIManager


def test_default_args():
    """Test default arguments"""
    cli = CLIManager()
    args = cli.parse_arguments([])
    
    # Check default values
    assert args.mode == "dev"
    assert args.urls is None
    assert args.url_file is None
    assert args.config == "config/config.yaml"
    
    # Get URLs (should be default URLs)
    urls = cli.get_urls_from_args(args)
    assert len(urls) > 0
    assert "https://pac.com.pk/" in urls
    
    print("✓ Default arguments test passed")


def test_custom_args():
    """Test custom arguments"""
    cli = CLIManager()
    args = cli.parse_arguments([
        "--mode=dev",  # Use dev mode to avoid requiring API key
        "--urls", "https://example.com", "https://example.org",
        "--max-workers", "5",
        "--max-depth", "2"
    ])
    
    # Check parsed values
    assert args.mode == "dev"
    assert args.urls == ["https://example.com", "https://example.org"]
    assert args.max_workers == 5
    assert args.max_depth == 2
    
    # Get URLs
    urls = cli.get_urls_from_args(args)
    assert len(urls) == 2
    assert "https://example.com" in urls
    assert "https://example.org" in urls
    
    print("✓ Custom arguments test passed")


def test_url_file(tmp_path):
    """Test URL file loading"""
    # Create test files
    txt_file = tmp_path / "urls.txt"
    csv_file = tmp_path / "urls.csv"
    json_file = tmp_path / "urls.json"
    
    # Write test data
    with open(txt_file, "w") as f:
        f.write("https://example.com\nhttps://example.org\n")
    
    with open(csv_file, "w") as f:
        f.write("https://example.net\nhttps://example.edu\n")
    
    with open(json_file, "w") as f:
        f.write('{"urls": ["https://example.io", "https://example.dev"]}')
    
    # Test TXT file
    cli = CLIManager()
    args = cli.parse_arguments(["--url-file", str(txt_file)])
    urls = cli.get_urls_from_args(args)
    assert len(urls) == 2
    assert "https://example.com" in urls
    assert "https://example.org" in urls
    
    # Test CSV file
    args = cli.parse_arguments(["--url-file", str(csv_file)])
    urls = cli.get_urls_from_args(args)
    assert len(urls) == 2
    assert "https://example.net" in urls
    assert "https://example.edu" in urls
    
    # Test JSON file
    args = cli.parse_arguments(["--url-file", str(json_file)])
    urls = cli.get_urls_from_args(args)
    assert len(urls) == 2
    assert "https://example.io" in urls
    assert "https://example.dev" in urls
    
    print("✓ URL file loading test passed")


def test_help_output():
    """Test help output"""
    cli = CLIManager()
    help_text = cli.get_usage_examples()
    
    # Check that help text contains examples
    assert "Examples:" in help_text
    assert "python -m scraper" in help_text
    assert "Development mode saves content" in help_text
    
    print("✓ Help output test passed")


def main():
    """Run all tests"""
    print("Testing CLI functionality...")
    
    # Create temporary directory for file tests
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_default_args()
        
        # Skip production mode test if no API key
        if os.environ.get("RAG_API_KEY"):
            test_custom_args()
        else:
            print("⚠ Skipping production mode test (RAG_API_KEY not set)")
        
        test_url_file(Path(tmp_dir))
        test_help_output()
    
    print("\nAll CLI tests passed!")


if __name__ == "__main__":
    main()