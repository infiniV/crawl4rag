#!/usr/bin/env python3
"""
Content Classification System Demo

This script demonstrates the content classification functionality
using sample content and the configured domain keywords.
"""

import yaml
from scraper.utils.classifier_factory import create_classifier_from_config


def main():
    """Demonstrate content classification functionality"""
    
    # Load configuration
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Create classifier
    classifier = create_classifier_from_config(config)
    
    # Sample content for testing different domains
    test_content = [
        {
            'title': 'Weather Forecast',
            'content': 'Tomorrow will be sunny with temperatures reaching 25°C. Climate patterns show increasing rainfall this season.',
            'expected_domain': 'weather'
        },
        {
            'title': 'Farm Equipment Guide',
            'content': 'Modern agricultural machinery includes tractors, harvesters, and irrigation equipment for efficient farm operations.',
            'expected_domain': 'farm'
        },
        {
            'title': 'Crop Disease Management',
            'content': 'Plant diseases can severely affect crop yields. Early detection of pest infestations is crucial for harvest success.',
            'expected_domain': 'crops'
        },
        {
            'title': 'Water Management Systems',
            'content': 'Efficient irrigation and drainage systems are essential for sustainable water usage in agriculture.',
            'expected_domain': 'water'
        },
        {
            'title': 'Agricultural Loans',
            'content': 'Farmers can access credit and insurance options to finance their agricultural operations and equipment purchases.',
            'expected_domain': 'banking'
        },
        {
            'title': 'Market Prices',
            'content': 'Commodity prices fluctuate based on market demand. Trade volumes affect agricultural product pricing.',
            'expected_domain': 'marketplace'
        },
        {
            'title': 'Organic Farming',
            'content': 'Sustainable agriculture practices focus on soil health and organic crop production methods.',
            'expected_domain': 'agriculture'
        },
        {
            'title': 'Random Content',
            'content': 'This is completely unrelated content about space exploration and rocket science.',
            'expected_domain': 'agriculture'  # Should fallback to default
        }
    ]
    
    print("Content Classification Demo")
    print("=" * 50)
    print()
    
    # Display classifier statistics
    stats = classifier.get_classification_stats()
    print(f"Classifier Configuration:")
    print(f"  Total Domains: {stats['total_domains']}")
    print(f"  Total Keywords: {stats['total_keywords']}")
    print(f"  Default Domain: {stats['default_domain']}")
    print(f"  Min Confidence: {stats['min_confidence_threshold']}")
    print()
    
    # Test each content sample
    for i, sample in enumerate(test_content, 1):
        print(f"Test {i}: {sample['title']}")
        print(f"Content: {sample['content'][:100]}...")
        
        # Classify content
        result = classifier.classify_content(
            content=sample['content'],
            metadata={'title': sample['title']}
        )
        
        print(f"Primary Domain: {result.primary_domain}")
        print(f"All Domains: {result.all_domains}")
        print(f"Confidence: {result.confidence:.3f}")
        
        # Show top 3 domain scores
        sorted_scores = sorted(result.scores.items(), key=lambda x: x[1], reverse=True)[:3]
        print("Top Scores:")
        for domain, score in sorted_scores:
            print(f"  {domain}: {score:.3f}")
        
        # Check if classification matches expectation
        expected = sample['expected_domain']
        if result.primary_domain == expected:
            print("✓ Classification matches expectation")
        else:
            print(f"⚠ Expected {expected}, got {result.primary_domain}")
        
        print("-" * 40)
        print()
    
    # Demonstrate domain keyword lookup
    print("Domain Keywords:")
    print("=" * 20)
    domain_keywords = classifier.get_domain_keywords()
    for domain, keywords in domain_keywords.items():
        print(f"{domain}: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
    
    print()
    print("Demo completed successfully!")


if __name__ == "__main__":
    main()