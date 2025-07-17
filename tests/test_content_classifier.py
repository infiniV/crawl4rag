"""
Tests for Content Classification System

Tests the ContentClassifier functionality including keyword-based classification,
relevance scoring, multi-domain assignment, and fallback behavior.
"""

import pytest
from scraper.processors.classifier import ContentClassifier, ClassificationResult


class TestContentClassifier:
    """Test suite for ContentClassifier"""
    
    @pytest.fixture
    def sample_domain_keywords(self):
        """Sample domain keywords for testing"""
        return {
            'agriculture': ['farm', 'crop', 'soil', 'organic', 'agriculture'],
            'water': ['irrigation', 'water', 'drainage', 'hydro'],
            'weather': ['weather', 'climate', 'forecast', 'meteorology'],
            'crops': ['crop', 'plant', 'disease', 'pest', 'harvest'],
            'farm': ['equipment', 'machinery', 'operation', 'management'],
            'marketplace': ['market', 'price', 'commodity', 'trade'],
            'banking': ['loan', 'insurance', 'finance', 'credit'],
            'chat': ['conversation', 'chat', 'dialogue', 'interaction']
        }
    
    @pytest.fixture
    def classifier(self, sample_domain_keywords):
        """Create ContentClassifier instance for testing"""
        return ContentClassifier(
            domain_keywords=sample_domain_keywords,
            default_domain="agriculture",
            min_confidence_threshold=0.1
        )
    
    def test_classifier_initialization(self, sample_domain_keywords):
        """Test ContentClassifier initialization"""
        classifier = ContentClassifier(
            domain_keywords=sample_domain_keywords,
            default_domain="agriculture"
        )
        
        assert classifier.default_domain == "agriculture"
        assert classifier.min_confidence_threshold == 0.1
        assert len(classifier.domain_keywords) == 8
        
        # Test that keywords are normalized to lowercase
        assert all(keyword.islower() for keywords in classifier.domain_keywords.values() 
                  for keyword in keywords)
    
    def test_invalid_default_domain(self, sample_domain_keywords):
        """Test initialization with invalid default domain"""
        with pytest.raises(ValueError, match="Default domain 'invalid' not found"):
            ContentClassifier(
                domain_keywords=sample_domain_keywords,
                default_domain="invalid"
            )
    
    def test_keyword_normalization(self):
        """Test keyword normalization functionality"""
        keywords = {
            'test': ['FARM', 'Crop', '  soil  ', 'ORGANIC', 'farm']  # duplicates and mixed case
        }
        classifier = ContentClassifier(keywords, default_domain="test")
        
        normalized = classifier.domain_keywords['test']
        assert normalized == ['farm', 'crop', 'soil', 'organic']  # lowercase, no duplicates
    
    def test_content_preprocessing(self, classifier):
        """Test content preprocessing"""
        content = "  This is a TEST with Special@Characters!!! and   extra   spaces  "
        processed = classifier._preprocess_content(content)
        
        assert processed == "this is a test with special characters and extra spaces"
    
    def test_keyword_matching(self, classifier):
        """Test keyword matching functionality"""
        content = "farm equipment and crop management for organic agriculture"
        keywords = ['farm', 'crop', 'organic', 'equipment']
        
        matches = classifier._calculate_keyword_matches(content, keywords)
        
        assert matches['farm'] == 1
        assert matches['crop'] == 1
        assert matches['organic'] == 1
        assert matches['equipment'] == 1
        assert 'nonexistent' not in matches
    
    def test_domain_score_calculation(self, classifier):
        """Test domain score calculation"""
        content = "organic farm with crop rotation and soil management"
        keywords = ['farm', 'crop', 'soil', 'organic']
        
        score = classifier._calculate_domain_score(content, 'agriculture', keywords)
        
        assert 0.0 <= score <= 1.0
        assert score > 0  # Should have positive score due to keyword matches
    
    def test_single_domain_classification(self, classifier):
        """Test classification with clear single domain match"""
        content = "Weather forecast shows rain tomorrow with climate change affecting meteorology patterns"
        
        result = classifier.classify_content(content)
        
        assert isinstance(result, ClassificationResult)
        assert result.primary_domain == "weather"
        assert "weather" in result.all_domains
        assert result.confidence > 0
        assert "weather" in result.scores
        assert result.scores["weather"] > 0
    
    def test_multi_domain_classification(self, classifier):
        """Test classification with multiple domain matches"""
        content = "Farm equipment for crop irrigation using water management systems"
        
        result = classifier.classify_content(content)
        
        assert isinstance(result, ClassificationResult)
        assert len(result.all_domains) >= 1
        assert result.confidence > 0
        
        # Should match multiple domains: farm, crops, water
        expected_domains = {'farm', 'crops', 'water', 'agriculture'}
        assert any(domain in expected_domains for domain in result.all_domains)
    
    def test_fallback_to_default_domain(self, classifier):
        """Test fallback to default domain for uncertain classifications"""
        content = "This is completely unrelated content about space exploration and rockets"
        
        result = classifier.classify_content(content)
        
        assert result.primary_domain == "agriculture"  # default domain
        assert result.all_domains == ["agriculture"]
        assert result.confidence == 0.0
    
    def test_empty_content_classification(self, classifier):
        """Test classification with empty content"""
        result = classifier.classify_content("")
        
        assert result.primary_domain == "agriculture"  # default domain
        assert result.all_domains == ["agriculture"]
        assert result.confidence == 0.0
    
    def test_classification_with_metadata(self, classifier):
        """Test classification including metadata"""
        content = "General farming practices"
        metadata = {
            'title': 'Weather Patterns and Climate Change',
            'description': 'Meteorological forecast analysis'
        }
        
        result = classifier.classify_content(content, metadata)
        
        # Should classify as weather due to metadata, not agriculture
        assert result.primary_domain == "weather"
        assert result.confidence > 0
    
    def test_get_domain_keywords(self, classifier):
        """Test getting domain keywords"""
        keywords = classifier.get_domain_keywords()
        
        assert isinstance(keywords, dict)
        assert len(keywords) == 8
        assert 'agriculture' in keywords
        assert 'water' in keywords
        
        # Ensure it returns a copy (modifications don't affect original)
        keywords['test'] = ['test']
        assert 'test' not in classifier.domain_keywords
    
    def test_calculate_relevance_score(self, classifier):
        """Test calculating relevance score for specific domain"""
        content = "Farm equipment and agricultural machinery for crop management"
        
        agriculture_score = classifier.calculate_relevance_score(content, 'agriculture')
        farm_score = classifier.calculate_relevance_score(content, 'farm')
        weather_score = classifier.calculate_relevance_score(content, 'weather')
        
        assert agriculture_score > 0
        assert farm_score > 0
        assert weather_score == 0  # No weather keywords in content
        
        # Agriculture and farm should have higher scores than weather
        assert agriculture_score > weather_score
        assert farm_score > weather_score
    
    def test_unknown_domain_relevance_score(self, classifier):
        """Test relevance score calculation for unknown domain"""
        content = "Some content"
        score = classifier.calculate_relevance_score(content, 'unknown_domain')
        
        assert score == 0.0
    
    def test_update_domain_keywords(self, classifier):
        """Test updating keywords for existing domain"""
        new_keywords = ['new', 'updated', 'keywords']
        classifier.update_domain_keywords('agriculture', new_keywords)
        
        assert classifier.domain_keywords['agriculture'] == new_keywords
    
    def test_add_new_domain(self, classifier):
        """Test adding new domain with keywords"""
        new_keywords = ['technology', 'innovation', 'digital']
        classifier.add_domain('technology', new_keywords)
        
        assert 'technology' in classifier.domain_keywords
        assert classifier.domain_keywords['technology'] == new_keywords
    
    def test_add_existing_domain(self, classifier):
        """Test adding domain that already exists (should update)"""
        original_keywords = classifier.domain_keywords['agriculture'].copy()
        new_keywords = ['updated', 'agriculture', 'keywords']
        
        classifier.add_domain('agriculture', new_keywords)
        
        assert classifier.domain_keywords['agriculture'] == new_keywords
        assert classifier.domain_keywords['agriculture'] != original_keywords
    
    def test_classification_stats(self, classifier):
        """Test getting classification system statistics"""
        stats = classifier.get_classification_stats()
        
        assert isinstance(stats, dict)
        assert stats['total_domains'] == 8
        assert stats['total_keywords'] > 0
        assert stats['default_domain'] == 'agriculture'
        assert stats['min_confidence_threshold'] == 0.1
        
        # Check per-domain stats
        assert 'agriculture_keywords' in stats
        assert stats['agriculture_keywords'] == len(classifier.domain_keywords['agriculture'])
    
    def test_confidence_threshold_filtering(self):
        """Test that confidence threshold properly filters domains"""
        keywords = {
            'high': ['specific', 'unique', 'distinctive'],
            'low': ['general', 'common']
        }
        
        classifier = ContentClassifier(
            domain_keywords=keywords,
            default_domain="high",
            min_confidence_threshold=0.5  # High threshold
        )
        
        # Content with no keyword matches should fall back to default
        content = "random unrelated content about space exploration"
        result = classifier.classify_content(content)
        
        # Should use default domain due to no matches
        assert result.primary_domain == "high"
    
    def test_word_boundary_matching(self, classifier):
        """Test that keyword matching respects word boundaries"""
        content = "farming is different from pharmacy"
        
        # Should match 'farm' in 'farming' but not in 'pharmacy'
        matches = classifier._calculate_keyword_matches(content, ['farm'])
        assert matches.get('farm', 0) == 1  # Only matches 'farming', not 'pharmacy'
    
    def test_case_insensitive_matching(self, classifier):
        """Test that keyword matching is case insensitive"""
        content = "FARM equipment and Crop management for ORGANIC agriculture"
        
        result = classifier.classify_content(content)
        
        # Should match despite different cases
        assert result.primary_domain in ['agriculture', 'farm', 'crops']
        assert result.confidence > 0


if __name__ == "__main__":
    pytest.main([__file__])