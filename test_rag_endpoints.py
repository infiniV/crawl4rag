#!/usr/bin/env python3
"""
Test script to discover RAG API endpoints and authentication method
"""

import asyncio
import aiohttp
import json


async def test_rag_endpoints():
    """Test different RAG API endpoints to discover the correct authentication method"""
    api_key = "ragnar_pzt3-FWkRbYxISfGVKqZnzpD_qDpZxxZLaTQGVdp_H4"
    base_url = "http://217.154.66.145:8000"
    
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("=== Testing RAG API Endpoints ===\n")
        
        # Test 1: Check if API is accessible
        print("1. Testing basic API accessibility...")
        try:
            async with session.get(f"{base_url}/") as response:
                print(f"   Status: {response.status}")
                if response.status == 200:
                    text = await response.text()
                    print(f"   Response: {text[:200]}...")
                else:
                    print(f"   Error: {await response.text()}")
        except Exception as e:
            print(f"   Exception: {e}")
        print()
        
        # Test 2: Check for docs endpoint
        print("2. Testing /docs endpoint...")
        try:
            async with session.get(f"{base_url}/docs") as response:
                print(f"   Status: {response.status}")
                if response.status == 200:
                    print("   ✅ Docs endpoint available")
                else:
                    print(f"   Error: {await response.text()}")
        except Exception as e:
            print(f"   Exception: {e}")
        print()
        
        # Test 3: Check for OpenAPI spec
        print("3. Testing /openapi.json endpoint...")
        try:
            async with session.get(f"{base_url}/openapi.json") as response:
                print(f"   Status: {response.status}")
                if response.status == 200:
                    spec = await response.json()
                    print("   ✅ OpenAPI spec available")
                    print("   Available paths:")
                    for path in list(spec.get('paths', {}).keys())[:10]:
                        print(f"     - {path}")
                    if len(spec.get('paths', {})) > 10:
                        print(f"     ... and {len(spec.get('paths', {})) - 10} more")
                else:
                    print(f"   Error: {await response.text()}")
        except Exception as e:
            print(f"   Exception: {e}")
        print()
        
        # Test 4: Try different auth endpoints
        auth_endpoints = [
            "/api/v1/auth/token",
            "/auth/token",
            "/token",
            "/api/auth",
            "/login",
            "/api/v1/login"
        ]
        
        print("4. Testing authentication endpoints...")
        for endpoint in auth_endpoints:
            try:
                auth_data = {
                    'api_key': api_key,
                    'grant_type': 'api_key'
                }
                
                async with session.post(f"{base_url}{endpoint}", json=auth_data) as response:
                    print(f"   {endpoint}: Status {response.status}")
                    if response.status in [200, 201]:
                        result = await response.json()
                        print(f"     ✅ Success: {list(result.keys())}")
                        return endpoint, result
                    elif response.status != 404:
                        error = await response.text()
                        print(f"     Error: {error[:100]}...")
            except Exception as e:
                print(f"   {endpoint}: Exception {e}")
        print()
        
        # Test 5: Try direct API key in headers
        print("5. Testing direct API key authentication...")
        headers = {
            'Authorization': f'Bearer {api_key}',
            'X-API-Key': api_key,
            'Api-Key': api_key
        }
        
        test_endpoints = [
            "/api/v1/documents",
            "/documents",
            "/api/documents",
            "/api/v1/documents/agriculture"
        ]
        
        for header_name, header_value in headers.items():
            print(f"   Testing with {header_name} header...")
            test_headers = {header_name: header_value}
            
            for endpoint in test_endpoints:
                try:
                    async with session.get(f"{base_url}{endpoint}", headers=test_headers) as response:
                        if response.status not in [404, 405]:  # Skip not found/method not allowed
                            print(f"     {endpoint}: Status {response.status}")
                            if response.status in [200, 201]:
                                print(f"       ✅ Success with {header_name}")
                                return endpoint, await response.json()
                except Exception as e:
                    pass
        print()
        
        # Test 6: Try to get available endpoints without auth
        print("6. Testing common endpoints without authentication...")
        common_endpoints = [
            "/health",
            "/status",
            "/api/health",
            "/api/status",
            "/api/v1/health",
            "/api/v1/status",
            "/ping"
        ]
        
        for endpoint in common_endpoints:
            try:
                async with session.get(f"{base_url}{endpoint}") as response:
                    if response.status == 200:
                        print(f"   ✅ {endpoint}: Available")
                        result = await response.text()
                        print(f"     Response: {result[:100]}...")
            except Exception as e:
                pass
        
        print("\n❌ Could not find working authentication method")
        return None, None


if __name__ == '__main__':
    asyncio.run(test_rag_endpoints())