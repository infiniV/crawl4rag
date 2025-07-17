#!/usr/bin/env python3
"""
Demo script for RAG API Uploader

This script demonstrates the RAG API integration functionality including:
- Authentication with RAG API
- Document upload to different domains
- Batch upload operations
- Error handling and retry logic
- Rate limiting management

Usage:
    python demo_rag_uploader.py
"""

import asyncio
import os
from datetime import datetime
from scraper.storage.rag_uploader import RAGUploader
from scraper.storage.prod_storage import ProdStorageManager
from scraper.core.base import ScrapedDocument


async def demo_rag_uploader():
    """Demonstrate RAG API uploader functionality"""
    print("=== RAG API Uploader Demo ===\n")
    
    # Configuration
    config = {
        'prod': {
            'rag_api_url': 'http://217.154.66.145:8000',
            'api_key_env': 'RAG_API_KEY'
        }
    }
    
    # Check if API key is available
    api_key = os.getenv('RAG_API_KEY')
    if not api_key:
        print("❌ RAG_API_KEY environment variable not set")
        print("   Set it with: export RAG_API_KEY=your_api_key")
        print("   This demo will show the functionality without actual API calls\n")
        
        # Demo without actual API calls
        await demo_without_api()
        return
    
    print(f"✅ API Key found: {api_key[:10]}...")
    print(f"✅ API URL: {config['prod']['rag_api_url']}\n")
    
    try:
        # Initialize RAG uploader
        print("🔧 Initializing RAG uploader...")
        uploader = RAGUploader(config)
        await uploader.initialize()
        print("✅ RAG uploader initialized successfully\n")
        
        # Create sample documents
        sample_docs = create_sample_documents()
        
        # Demo 1: Single document upload
        print("📤 Demo 1: Single Document Upload")
        print("-" * 40)
        doc = sample_docs[0]
        print(f"Uploading: {doc.title}")
        print(f"Domain: agriculture")
        
        try:
            doc_id = await uploader.upload_document(doc, 'agriculture')
            print(f"✅ Upload successful! Document ID: {doc_id}")
        except Exception as e:
            print(f"❌ Upload failed: {str(e)}")
        print()
        
        # Demo 2: Batch upload
        print("📤 Demo 2: Batch Document Upload")
        print("-" * 40)
        print(f"Uploading {len(sample_docs)} documents to water domain")
        
        try:
            doc_ids = await uploader.upload_batch(sample_docs, 'water')
            successful = len([doc_id for doc_id in doc_ids if doc_id])
            print(f"✅ Batch upload completed! {successful}/{len(sample_docs)} successful")
            for i, doc_id in enumerate(doc_ids):
                if doc_id:
                    print(f"   Document {i+1}: {doc_id}")
                else:
                    print(f"   Document {i+1}: Failed")
        except Exception as e:
            print(f"❌ Batch upload failed: {str(e)}")
        print()
        
        # Demo 3: Upload statistics
        print("📊 Demo 3: Upload Statistics")
        print("-" * 40)
        stats = uploader.get_upload_stats()
        print(f"Total uploads: {stats['total_uploads']}")
        print(f"Successful uploads: {stats['successful_uploads']}")
        print(f"Failed uploads: {stats['failed_uploads']}")
        print(f"Success rate: {stats['success_rate']:.2%}")
        print(f"Retries: {stats['retries']}")
        print(f"Rate limit hits: {stats['rate_limit_hits']}")
        print()
        
        # Demo 4: Production Storage Manager
        print("🏭 Demo 4: Production Storage Manager")
        print("-" * 40)
        storage_config = {'storage': config}
        storage = ProdStorageManager(storage_config)
        await storage.initialize()
        
        # Upload using storage manager
        doc = sample_docs[-1]
        print(f"Uploading via storage manager: {doc.title}")
        try:
            doc_id = await storage.save_document(doc, 'crops')
            print(f"✅ Storage upload successful! Document ID: {doc_id}")
        except Exception as e:
            print(f"❌ Storage upload failed: {str(e)}")
        
        # Get storage stats
        storage_stats = storage.get_storage_stats()
        print(f"Storage mode: {storage_stats['mode']}")
        print(f"Total documents: {storage_stats['total_documents']}")
        print()
        
        # Cleanup
        await storage.cleanup()
        await uploader.cleanup()
        print("✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")


async def demo_without_api():
    """Demo functionality without actual API calls"""
    print("🔧 Demo Mode: Showing functionality without API calls\n")
    
    # Create sample documents
    sample_docs = create_sample_documents()
    
    print("📄 Sample Documents Created:")
    print("-" * 40)
    for i, doc in enumerate(sample_docs, 1):
        print(f"{i}. {doc.title}")
        print(f"   URL: {doc.url}")
        print(f"   Content length: {len(doc.content)} chars")
        print(f"   Domain classifications: {doc.domain_classifications}")
        print()
    
    print("🔧 RAG Uploader Configuration:")
    print("-" * 40)
    config = {
        'prod': {
            'rag_api_url': 'http://217.154.66.145:8000',
            'api_key_env': 'RAG_API_KEY'
        }
    }
    
    uploader = RAGUploader(config)
    print(f"API URL: {uploader.api_url}")
    print(f"Rate limit: {uploader.rate_limit_requests} requests per {uploader.rate_limit_window} seconds")
    print(f"Max retries: {uploader.max_retries}")
    print(f"Base retry delay: {uploader.base_retry_delay} seconds")
    print(f"Max retry delay: {uploader.max_retry_delay} seconds")
    print()
    
    print("🎯 Available Domain Endpoints:")
    print("-" * 40)
    for domain, endpoint in uploader.domain_endpoints.items():
        print(f"{domain}: {endpoint}")
    print()
    
    print("📊 Retry Delay Calculation Demo:")
    print("-" * 40)
    for attempt in range(5):
        delay = uploader._calculate_retry_delay(attempt)
        print(f"Attempt {attempt}: {delay:.2f} seconds")
    print()
    
    print("✅ Demo completed! Set RAG_API_KEY to test actual API integration.")


def create_sample_documents():
    """Create sample documents for testing"""
    documents = []
    
    # Agriculture document
    doc1 = ScrapedDocument(
        url='https://example.com/agriculture/crop-rotation',
        title='Sustainable Crop Rotation Practices',
        content='Crop rotation is a fundamental agricultural practice that involves growing different types of crops in the same area across different seasons or years. This practice helps maintain soil health, reduce pest and disease pressure, and improve overall farm productivity.',
        markdown='# Sustainable Crop Rotation Practices\n\nCrop rotation is a fundamental agricultural practice that involves growing different types of crops in the same area across different seasons or years. This practice helps maintain soil health, reduce pest and disease pressure, and improve overall farm productivity.',
        metadata={'source': 'agriculture_website', 'category': 'farming_practices'},
        media_catalog=[],
        domain_classifications=['agriculture', 'crops'],
        timestamp=datetime.now(),
        content_hash='crop_rotation_hash_123',
        processing_time=2.1,
        retry_count=0
    )
    documents.append(doc1)
    
    # Water management document
    doc2 = ScrapedDocument(
        url='https://example.com/water/irrigation-systems',
        title='Modern Irrigation Systems for Efficient Water Use',
        content='Modern irrigation systems are designed to maximize water efficiency while ensuring optimal crop growth. Drip irrigation, sprinkler systems, and smart irrigation controllers are revolutionizing how farmers manage water resources.',
        markdown='# Modern Irrigation Systems for Efficient Water Use\n\nModern irrigation systems are designed to maximize water efficiency while ensuring optimal crop growth. Drip irrigation, sprinkler systems, and smart irrigation controllers are revolutionizing how farmers manage water resources.',
        metadata={'source': 'water_management_site', 'category': 'irrigation'},
        media_catalog=[{'type': 'image', 'url': 'https://example.com/irrigation.jpg', 'alt': 'Drip irrigation system'}],
        domain_classifications=['water', 'agriculture'],
        timestamp=datetime.now(),
        content_hash='irrigation_hash_456',
        processing_time=1.8,
        retry_count=0
    )
    documents.append(doc2)
    
    # Weather document
    doc3 = ScrapedDocument(
        url='https://example.com/weather/climate-change-farming',
        title='Climate Change Impact on Agricultural Practices',
        content='Climate change is significantly affecting agricultural practices worldwide. Farmers must adapt to changing precipitation patterns, temperature fluctuations, and extreme weather events to maintain productive farming operations.',
        markdown='# Climate Change Impact on Agricultural Practices\n\nClimate change is significantly affecting agricultural practices worldwide. Farmers must adapt to changing precipitation patterns, temperature fluctuations, and extreme weather events to maintain productive farming operations.',
        metadata={'source': 'climate_research', 'category': 'climate_impact'},
        media_catalog=[],
        domain_classifications=['weather', 'agriculture'],
        timestamp=datetime.now(),
        content_hash='climate_hash_789',
        processing_time=2.5,
        retry_count=0
    )
    documents.append(doc3)
    
    return documents


if __name__ == '__main__':
    asyncio.run(demo_rag_uploader())