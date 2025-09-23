#!/usr/bin/env python3
"""
Test script for AI reply settings API
Tests the fix for 422 validation error
"""

import json
import requests

# Test data that was causing 422 error before
test_settings = {
    "autoReplyEnabled": True,
    "replyTone": "friendly",
    "minReplyLength": 50,
    "maxReplyLength": 200,
    "brandVoice": None,  # This was causing issues
    "greetingTemplate": "",
    "closingTemplate": "",
    "seoKeywords": [],
    "autoApprovalDelayHours": 48,
    "operationType": "both"  # This field was missing from Pydantic model
}

# Backend URL
backend_url = "https://helper-backend-4ilp.onrender.com"

# Test store ID (we'll use a valid UUID format for testing)
test_store_id = "12345678-1234-1234-1234-123456789012"

print("Testing AI Reply Settings API...")
print(f"Backend URL: {backend_url}")
print(f"Test Store ID: {test_store_id}")
print("\nSending test data:")
print(json.dumps(test_settings, indent=2))

try:
    # Test POST request (this was failing with 422 before)
    response = requests.post(
        f"{backend_url}/api/reply-settings/{test_store_id}",
        headers={"Content-Type": "application/json"},
        json=test_settings,
        timeout=10
    )

    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")

    if response.status_code == 200:
        print("SUCCESS! 422 validation error has been fixed!")
        response_data = response.json()
        print("Response Data:")
        print(json.dumps(response_data, indent=2))
    elif response.status_code == 422:
        print("STILL FAILING: 422 validation error persists")
        try:
            error_data = response.json()
            print("Error Details:")
            print(json.dumps(error_data, indent=2))
        except:
            print("Error Response (not JSON):")
            print(response.text)
    else:
        print(f"Unexpected status code: {response.status_code}")
        print("Response:")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"Network Error: {e}")
except Exception as e:
    print(f"Unexpected Error: {e}")

print("\nTesting GET endpoint as well...")

try:
    # Test GET request
    get_response = requests.get(
        f"{backend_url}/api/reply-settings/{test_store_id}",
        timeout=10
    )

    print(f"GET Response Status: {get_response.status_code}")

    if get_response.status_code == 200:
        print("GET endpoint working!")
        get_data = get_response.json()
        print("GET Response Data:")
        print(json.dumps(get_data, indent=2))
    else:
        print(f"GET Response: {get_response.text}")

except Exception as e:
    print(f"GET Error: {e}")

print("\nTest completed!")