#!/usr/bin/env python3
"""
Test script to debug production API issues
Run this to test your production API multiple times
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict

# Configuration
PRODUCTION_URL = "https://umadevi-pride-finance-backend-7dhh.vercel.app"
LOCAL_URL = "http://localhost:8000"

async def test_api(session: aiohttp.ClientSession, url: str, token: str, test_name: str) -> Dict:
    """Test a single API call"""
    try:
        start_time = time.time()
        async with session.get(
            f"{url}/api/v1/vehicles/getAll",
            headers={"Authorization": f"Bearer {token}"}
        ) as response:
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status == 200:
                data = await response.json()
                vehicle_count = len(data) if isinstance(data, list) else 0
                return {
                    "test_name": test_name,
                    "status": "SUCCESS",
                    "vehicle_count": vehicle_count,
                    "response_time": round(response_time, 3),
                    "status_code": response.status,
                    "data_preview": data[:2] if vehicle_count > 0 else []
                }
            else:
                error_text = await response.text()
                return {
                    "test_name": test_name,
                    "status": "ERROR",
                    "vehicle_count": 0,
                    "response_time": round(response_time, 3),
                    "status_code": response.status,
                    "error": error_text
                }
    except Exception as e:
        return {
            "test_name": test_name,
            "status": "EXCEPTION",
            "vehicle_count": 0,
            "response_time": 0,
            "status_code": 0,
            "error": str(e)
        }

async def get_auth_token(session: aiohttp.ClientSession, url: str) -> str:
    """Get authentication token"""
    try:
        async with session.post(
            f"{url}/api/v1/auth/login",
            json={"password": "6201"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("access_token", "")
            else:
                print(f"Failed to get auth token: {response.status}")
                return ""
    except Exception as e:
        print(f"Exception getting auth token: {e}")
        return ""

async def run_tests():
    """Run multiple API tests"""
    print("🚀 Starting API Tests...")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test local first
        print("📡 Testing LOCAL API...")
        local_token = await get_auth_token(session, LOCAL_URL)
        if local_token:
            local_results = []
            for i in range(5):
                result = await test_api(session, LOCAL_URL, local_token, f"Local Test {i+1}")
                local_results.append(result)
                await asyncio.sleep(1)
            
            print("\n📊 LOCAL RESULTS:")
            for result in local_results:
                status_emoji = "✅" if result["status"] == "SUCCESS" else "❌"
                print(f"{status_emoji} {result['test_name']}: {result['vehicle_count']} vehicles, {result['response_time']}s")
        
        print("\n" + "=" * 60)
        
        # Test production
        print("🌐 Testing PRODUCTION API...")
        prod_token = await get_auth_token(session, PRODUCTION_URL)
        if prod_token:
            prod_results = []
            for i in range(10):  # More tests for production
                result = await test_api(session, PRODUCTION_URL, prod_token, f"Production Test {i+1}")
                prod_results.append(result)
                await asyncio.sleep(2)  # Longer delay for production
            
            print("\n📊 PRODUCTION RESULTS:")
            success_count = 0
            empty_count = 0
            
            for result in prod_results:
                status_emoji = "✅" if result["status"] == "SUCCESS" else "❌"
                if result["status"] == "SUCCESS":
                    success_count += 1
                    if result["vehicle_count"] == 0:
                        empty_count += 1
                        status_emoji = "⚠️"  # Empty array warning
                
                print(f"{status_emoji} {result['test_name']}: {result['vehicle_count']} vehicles, {result['response_time']}s")
            
            print(f"\n📈 SUMMARY:")
            print(f"   Total Tests: {len(prod_results)}")
            print(f"   Successful: {success_count}")
            print(f"   Empty Arrays: {empty_count}")
            print(f"   Success Rate: {(success_count/len(prod_results)*100):.1f}%")
            print(f"   Empty Array Rate: {(empty_count/len(prod_results)*100):.1f}%")
            
            if empty_count > 0:
                print(f"\n⚠️  WARNING: {empty_count} empty array responses detected!")
                print("   This indicates intermittent database connection issues.")
        else:
            print("❌ Failed to get production auth token")

if __name__ == "__main__":
    asyncio.run(run_tests())
