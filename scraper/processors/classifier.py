"""
Content Classification System for RAG Domains

This module provides intelligent content categorization for RAG domain assignment
using keyword-based classification with relevance scoring.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    """Result of content classification"""
    primary_domain: str
    all_domains: List[str]
    scores: Dict[str, float]
    confidence: float


class ContentClassifier:
    """
    Intelligent content classifier for RAG domain assignment.
    
    Uses keyword-based classification with relevance scoring to determine
    the most appropriate RAG domain(s) for content.
    """
    
    def __init__(self, domain_keywords: Dict[str, List[str]], 
                 default_domain: str = "agriculture",
                 min_confidence_threshold: float = 0.1):
        """
        Initialize the content classifier.
        
        Args:
            domain_keywords: Dictionary mapping domain names to keyword lists
            default_domain: Fallback domain for uncertain classifications
            min_confidence_threshold: Minimum confidence score for domain assignment
        """
        self.domain_keywords = self._normalize_keywords(domain_keywords)
        self.default_domain = default_domain
        self.min_confidence_threshold = min_confidence_threshold
        self.logger = logging.getLogger(__name__)
        
        # Validate that default domain exists in keywords
        if default_domain not in self.domain_keywords:
            raise ValueError(f"Default domain '{default_domain}' not found in domain keywords")
    
    def _normalize_keywords(self, domain_keywords: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Normalize keywords to lowercase and remove duplicates.
        
        Args:
            domain_keywords: Raw domain keywords dictionary
            
        Returns:
            Normalized domain keywords dictionary
        """
        normalized = {}
        for domain, keywords in domain_keywords.items():
            # Convert to lowercase and remove duplicates while preserving order
            normalized_keywords = []
            seen = set()
            for keyword in keywords:
                lower_keyword = keyword.lower().strip()
                if lower_keyword and lower_keyword not in seen:
                    normalized_keywords.append(lower_keyword)
                    seen.add(lower_keyword)
            normalized[domain] = normalized_keywords
        return normalized
    
    def _preprocess_content(self, content: str) -> str:
        """
        Preprocess content for classification.
        
        Args:
            content: Raw content text
            
        Returns:
            Preprocessed content text
        """
        if not content:
            return ""
        
        # Convert to lowercase
        content = content.lower()
        
        # Remove special characters but keep word boundaries
        content = re.sub(r'[^\w\s-]', ' ', content)
        
        # Remove extra whitespace and normalize
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _calculate_keyword_matches(self, content: str, keywords: List[str]) -> Dict[str, int]:
        """
        Calculate keyword matches in content.
        
        Args:
            content: Preprocessed content text
            keywords: List of keywords to search for
            
        Returns:
            Dictionary mapping keywords to match counts
        """
        matches = {}
        
        for keyword in keywords:
            # Match keyword as substring of words (e.g., "farm" matches "farming")
            # but not as substring within other words (e.g., "farm" doesn't match "pharmacy")
            pattern = r'\b' + re.escape(keyword) + r'\w*'
            match_count = len(re.findall(pattern, content))
            if match_count > 0:
                matches[keyword] = match_count
        
        return matches
    
    def _calculate_domain_score(self, content: str, domain: str, keywords: List[str]) -> float:
        """
        Calculate relevance score for a specific domain.
        
        Args:
            content: Preprocessed content text
            domain: Domain name
            keywords: Keywords for the domain
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        if not content or not keywords:
            return 0.0
        
        # Get keyword matches
        matches = self._calculate_keyword_matches(content, keywords)
        
        if not matches:
            return 0.0
        
        # Calculate base score from keyword frequency
        total_matches = sum(matches.values())
        unique_keywords_matched = len(matches)
        total_keywords = len(keywords)
        
        # Score components:
        # 1. Keyword coverage (what percentage of domain keywords were found)
        coverage_score = unique_keywords_matched / total_keywords
        
        # 2. Match frequency (how often keywords appear)
        content_words = len(content.split())
        frequency_score = min(total_matches / max(content_words, 1), 1.0)
        
        # 3. Keyword diversity bonus (reward matching multiple different keywords)
        diversity_bonus = min(unique_keywords_matched / 5, 0.2)  # Max 20% bonus
        
        # Combine scores with weights
        final_score = (
            coverage_score * 0.5 +      # 50% weight on coverage
            frequency_score * 0.4 +     # 40% weight on frequency
            diversity_bonus             # 20% bonus for diversity
        )
        
        return min(final_score, 1.0)
    
    def classify_content(self, content: str, metadata: Optional[Dict] = None) -> ClassificationResult:
        """
        Classify content and determine appropriate RAG domain(s).
        
        Args:
            content: Content text to classify
            metadata: Optional metadata that might influence classification
            
        Returns:
            ClassificationResult with domain assignments and scores
        """
        if not content or not content.strip():
            self.logger.warning("Empty content provided for classification, using default domain")
            return ClassificationResult(
                primary_domain=self.default_domain,
                all_domains=[self.default_domain],
                scores={self.default_domain: 0.0},
                confidence=0.0
            )
        
        # Preprocess content
        processed_content = self._preprocess_content(content)
        
        # Include metadata in content if available
        if metadata:
            title = metadata.get('title', '')
            description = metadata.get('description', '')
            if title:
                processed_content = f"{title} {processed_content}"
            if description:
                processed_content = f"{description} {processed_content}"
            processed_content = self._preprocess_content(processed_content)
        
        # Calculate scores for each domain
        domain_scores = {}
        for domain, keywords in self.domain_keywords.items():
            score = self._calculate_domain_score(processed_content, domain, keywords)
            domain_scores[domain] = score
        
        # Sort domains by score
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Determine primary domain and qualifying domains
        if not sorted_domains or sorted_domains[0][1] < self.min_confidence_threshold:
            # No domain meets minimum threshold, use default
            primary_domain = self.default_domain
            qualifying_domains = [self.default_domain]
            max_confidence = 0.0
            self.logger.info(f"No domain met confidence threshold, using default: {self.default_domain}")
        else:
            primary_domain = sorted_domains[0][0]
            max_confidence = sorted_domains[0][1]
            
            # Include all domains that meet the threshold
            qualifying_domains = [
                domain for domain, score in sorted_domains 
                if score >= self.min_confidence_threshold
            ]
            
            # If no domains meet threshold after all, fall back to default
            if not qualifying_domains:
                primary_domain = self.default_domain
                qualifying_domains = [self.default_domain]
                max_confidence = 0.0
        
        # Log classification result
        self.logger.debug(f"Content classified - Primary: {primary_domain}, "
                         f"All: {qualifying_domains}, Confidence: {max_confidence:.3f}")
        
        return ClassificationResult(
            primary_domain=primary_domain,
            all_domains=qualifying_domains,
            scores=domain_scores,
            confidence=max_confidence
        )
    
    def get_domain_keywords(self) -> Dict[str, List[str]]:
        """
        Get the current domain keywords configuration.
        
        Returns:
            Dictionary mapping domain names to keyword lists
        """
        return self.domain_keywords.copy()
    
    def calculate_relevance_score(self, content: str, domain: str) -> float:
        """
        Calculate relevance score for specific domain.
        
        Args:
            content: Content text to analyze
            domain: Domain name to calculate score for
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        if domain not in self.domain_keywords:
            self.logger.warning(f"Unknown domain: {domain}")
            return 0.0
        
        processed_content = self._preprocess_content(content)
        keywords = self.domain_keywords[domain]
        
        return self._calculate_domain_score(processed_content, domain, keywords)
    
    def update_domain_keywords(self, domain: str, keywords: List[str]) -> None:
        """
        Update keywords for a specific domain.
        
        Args:
            domain: Domain name to update
            keywords: New list of keywords for the domain
        """
        self.domain_keywords[domain] = self._normalize_keywords({domain: keywords})[domain]
        self.logger.info(f"Updated keywords for domain '{domain}': {len(keywords)} keywords")
    
    def add_domain(self, domain: str, keywords: List[str]) -> None:
        """
        Add a new domain with keywords.
        
        Args:
            domain: New domain name
            keywords: List of keywords for the domain
        """
        if domain in self.domain_keywords:
            self.logger.warning(f"Domain '{domain}' already exists, updating keywords")
        
        self.update_domain_keywords(domain, keywords)
    
    def get_classification_stats(self) -> Dict[str, int]:
        """
        Get statistics about the classification system.
        
        Returns:
            Dictionary with classification system statistics
        """
        stats = {
            'total_domains': len(self.domain_keywords),
            'total_keywords': sum(len(keywords) for keywords in self.domain_keywords.values()),
            'default_domain': self.default_domain,
            'min_confidence_threshold': self.min_confidence_threshold
        }
        
        # Add per-domain keyword counts
        for domain, keywords in self.domain_keywords.items():
            stats[f'{domain}_keywords'] = len(keywords)
        
        return stats