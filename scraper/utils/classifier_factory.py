"""
Factory for creating ContentClassifier instances from configuration

This module provides utilities for creating ContentClassifier instances
from the application configuration.
"""

import logging
from typing import Dict, Any
from scraper.processors.classifier import ContentClassifier


def create_classifier_from_config(config: Dict[str, Any]) -> ContentClassifier:
    """
    Create a ContentClassifier instance from configuration.
    
    Args:
        config: Configuration dictionary containing domain keywords
        
    Returns:
        Configured ContentClassifier instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    logger = logging.getLogger(__name__)
    
    # Extract domain keywords from config
    domains_config = config.get('domains', {})
    if not domains_config:
        raise ValueError("No domains configuration found")
    
    # Get classifier settings
    classifier_config = config.get('classifier', {})
    default_domain = classifier_config.get('default_domain', 'agriculture')
    min_confidence_threshold = classifier_config.get('min_confidence_threshold', 0.1)
    
    # Validate that default domain exists in domains
    if default_domain not in domains_config:
        logger.warning(f"Default domain '{default_domain}' not found in domains config, "
                      f"using first available domain")
        default_domain = next(iter(domains_config.keys()))
    
    # Create classifier
    classifier = ContentClassifier(
        domain_keywords=domains_config,
        default_domain=default_domain,
        min_confidence_threshold=min_confidence_threshold
    )
    
    logger.info(f"Created ContentClassifier with {len(domains_config)} domains, "
               f"default: {default_domain}, threshold: {min_confidence_threshold}")
    
    return classifier


def load_classifier_from_yaml(config_path: str) -> ContentClassifier:
    """
    Load ContentClassifier from YAML configuration file.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configured ContentClassifier instance
    """
    import yaml
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return create_classifier_from_config(config)