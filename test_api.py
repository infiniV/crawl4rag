#!/usr/bin/env python3
import requests
import json

def test_api():
    api_key = "ragnar_pzt3-FWkRbYxISfGVKqZnzpD_qDpZxxZLaTQGVdp_H4"
    base_url = "http://217.154.66.145:8000"
    
    # Test health endpoint (no auth required)
    print("Testing health endpoint...")
    health_response = requests.get(f"{base_url}/health")
    print(f"Status: {health_response.status_code}")
    print(f"Response: {health_response.json()}")
    print("-" * 50)
    
    # Test domains endpoint (auth required)
    print("Testing domains endpoint...")
    headers = {"Authorization": f"Bearer {api_key}"}
    domains_response = requests.get(f"{base_url}/api/v1/domains", headers=headers)
    print(f"Status: {domains_response.status_code}")
    print(f"Response: {domains_response.text[:500]}...")
    print("-" * 50)
    
    # Test API key info endpoint
    print("Testing API key info endpoint...")
    me_response = requests.get(f"{base_url}/auth/me", headers=headers)
    print(f"Status: {me_response.status_code}")
    print(f"Response: {me_response.text[:500]}...")
    print("-" * 50)
    
    # Test document upload
    print("Testing document upload...")
    document_data = {
        "text": "This is a test document for the RAG API.",
        "metadata": {
            "source": "test",
            "type": "test"
        }
    }
    upload_response = requests.post(
        f"{base_url}/api/v1/documents/agriculture",
        headers=headers,
        json=document_data
    )
    print(f"Status: {upload_response.status_code}")
    print(f"Response: {upload_response.text[:500]}...")

if __name__ == "__main__":
    test_api()