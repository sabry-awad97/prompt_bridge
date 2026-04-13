"""Simple test script to make a ChatGPT request."""

import json

import requests

# Server URL
BASE_URL = "http://localhost:7777"


def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.status_code == 200


def test_chatgpt_request():
    """Test ChatGPT chat completion."""
    print("Testing ChatGPT chat completion...")

    payload = {
        "provider": "chatgpt",
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": "Hello! Please respond with just 'Hi there!' to confirm you're working.",
            }
        ],
    }

    print(f"Request payload: {json.dumps(payload, indent=2)}")
    print("\nSending request...")

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        timeout=120,  # 2 minutes timeout
    )

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")

        # Extract the assistant's message
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0]["message"]["content"]
            print(f"\n✅ ChatGPT Response: {message}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Prompt Bridge - ChatGPT Test")
    print("=" * 60)
    print()

    # Test health first
    if test_health():
        print("✅ Health check passed\n")
        print("=" * 60)
        print()

        # Test ChatGPT request
        if test_chatgpt_request():
            print("\n✅ ChatGPT test passed!")
        else:
            print("\n❌ ChatGPT test failed!")
    else:
        print("❌ Health check failed!")
