"""Test script for streaming debug endpoints."""

import requests
import json

BASE_URL = "http://localhost:7777"

def test_analyze_streaming():
    """Test the streaming analysis endpoint."""
    print("🔍 Testing ChatGPT Streaming Analysis")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/debug/chatgpt/analyze",
        params={"prompt": "Count from 1 to 5"},
        timeout=120
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Analysis complete!")
        print(f"\nFinal text: {data['final_text']}")
        print(f"Chunks collected: {data['chunks_collected']}")
        print(f"\nChunk details:")
        
        for i, chunk in enumerate(data['chunks'], 1):
            metadata = chunk['metadata']
            print(f"\n  Chunk {i}:")
            print(f"    Elapsed: {metadata.get('elapsed', 0):.3f}s")
            print(f"    Text length: {chunk['text_length']}")
            print(f"    Preview: {chunk['text_preview']}")
            if metadata.get('is_complete'):
                print(f"    ✓ Complete")
                if 'summary' in metadata:
                    summary = metadata['summary']
                    print(f"\n  Summary:")
                    print(f"    Total time: {summary.get('total_time', 0):.3f}s")
                    print(f"    Chunk count: {summary.get('chunk_count', 0)}")
                    print(f"    Avg interval: {summary.get('avg_interval', 0):.3f}s")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

def test_sse_streaming():
    """Test the SSE streaming endpoint."""
    print("\n\n📡 Testing SSE Streaming")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/debug/chatgpt/stream-test",
        params={"prompt": "Say hello and count to 3"},
        stream=True,
        timeout=120
    )
    
    if response.status_code == 200:
        print("✅ Streaming started...\n")
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)
                        event = data.get('event')
                        
                        if event == 'start':
                            print("🚀 Stream started")
                        elif event == 'chunk':
                            delta = data.get('delta', '')
                            elapsed = data.get('elapsed', 0)
                            print(f"📝 [{elapsed:.2f}s] {delta}", end='', flush=True)
                        elif event == 'done':
                            print(f"\n\n✅ Stream complete!")
                            print(f"Final text: {data.get('final_text', '')}")
                    except json.JSONDecodeError:
                        print(f"⚠️  Invalid JSON: {data_str}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("🧪 Prompt Bridge Streaming Debug Tests\n")
    
    try:
        # Test 1: Analyze streaming behavior
        test_analyze_streaming()
        
        # Test 2: Test SSE streaming
        test_sse_streaming()
        
        print("\n\n" + "=" * 60)
        print("✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to server")
        print("Make sure the server is running: uv run prompt-bridge start")
    except Exception as e:
        print(f"❌ Error: {e}")
