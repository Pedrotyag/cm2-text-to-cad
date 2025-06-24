#!/usr/bin/env python3
"""
Debug script for Ollama streaming
Run this to test direct streaming connection to Ollama
"""

import os
import json
import time
import requests
from dotenv import load_dotenv

def test_ollama_streaming():
    """Test Ollama streaming directly"""
    print("🔍 Testing Ollama Streaming Connection...")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    
    # Configuration
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "")
    ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "600"))
    
    print(f"🌐 Server: {ollama_url}")
    print(f"🤖 Model: {ollama_model}")
    print(f"⏱️  Timeout: {ollama_timeout}s ({ollama_timeout//60}m)")
    print()
    
    if not ollama_model:
        print("❌ OLLAMA_MODEL not configured in .env")
        return False
    
    # Simple test prompt
    test_prompt = """Create a simple cube using CadQuery. Respond with JSON containing:
{
    "intention_type": "creation",
    "response_text": "Creating a 10mm cube",
    "execution_plan": {
        "id": "cube_001",
        "description": "Simple cube creation",
        "cadquery_code": "import cadquery as cq\\nresult = cq.Workplane().box(10, 10, 10)"
    }
}"""
    
    payload = {
        "model": ollama_model,
        "prompt": test_prompt,
        "stream": True,
        "options": {
            "temperature": 0.1,
            "num_predict": 1000,
            "top_p": 0.9,
            "top_k": 40
        }
    }
    
    print(f"📝 Sending test prompt ({len(test_prompt)} chars)...")
    print(f"🎯 Prompt preview: '{test_prompt[:100]}...'")
    print()
    
    start_time = time.time()
    
    try:
        print(f"🚀 Making request to {ollama_url}/api/generate...")
        
        response = requests.post(
            f"{ollama_url}/api/generate",
            json=payload,
            timeout=ollama_timeout,
            stream=True
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        print(f"✅ Connection established (status: {response.status_code})")
        print("🔄 Starting to receive streaming data...")
        print("-" * 60)
        
        # Process streaming response
        full_response = ""
        chunk_count = 0
        last_log_time = time.time()
        
        for line in response.iter_lines():
            if line:
                chunk_count += 1
                current_time = time.time()
                elapsed = current_time - start_time
                
                try:
                    chunk_data = json.loads(line.decode('utf-8'))
                    
                    # Log every chunk for debugging
                    print(f"📦 Chunk {chunk_count} ({elapsed:.1f}s): {json.dumps(chunk_data)}")
                    
                    # Check for errors
                    if 'error' in chunk_data:
                        print(f"❌ Error in chunk: {chunk_data['error']}")
                        return False
                    
                    # Add partial response
                    if 'response' in chunk_data:
                        partial_response = chunk_data['response']
                        full_response += partial_response
                        
                        if chunk_count == 1:
                            print(f"🎉 First response received!")
                    
                    # Check if done
                    if chunk_data.get('done', False):
                        total_time = time.time() - start_time
                        print("-" * 60)
                        print(f"✅ Stream completed!")
                        print(f"⏱️  Total time: {total_time:.1f}s")
                        print(f"📈 Total chunks: {chunk_count}")
                        print(f"📝 Response length: {len(full_response)} chars")
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️  Invalid JSON chunk: {line[:100]}...")
                    print(f"   Error: {e}")
                    continue
        
        print()
        print("📄 FULL RESPONSE:")
        print("=" * 60)
        print(full_response)
        print("=" * 60)
        
        if not full_response:
            print("❌ No response received!")
            return False
        
        # Try to parse as JSON
        try:
            response_json = json.loads(full_response)
            print("✅ Response is valid JSON")
            print(f"🎯 Intention type: {response_json.get('intention_type', 'N/A')}")
        except json.JSONDecodeError:
            print("⚠️  Response is not valid JSON (this might be expected for some models)")
        
        print()
        print("🎉 Streaming test completed successfully!")
        return True
        
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"⏰ Request timed out after {elapsed:.1f}s")
        print(f"   Configured timeout: {ollama_timeout}s")
        print("💡 Try increasing OLLAMA_TIMEOUT or using a smaller model")
        return False
        
    except requests.exceptions.ConnectionError as e:
        print(f"🔌 Connection error: {e}")
        print("💡 Make sure Ollama is running with: ollama serve")
        return False
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"💥 Unexpected error after {elapsed:.1f}s: {e}")
        return False

def check_ollama_status():
    """Quick check of Ollama status"""
    print("🔍 Checking Ollama Status...")
    
    load_dotenv()
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    try:
        # Check if service is running
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            print(f"✅ Ollama is running at {ollama_url}")
            print(f"📦 Available models: {model_names}")
            return True
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("💡 Start Ollama with: ollama serve")
        return False

if __name__ == "__main__":
    print("🧪 Ollama Streaming Debug Tool")
    print("=" * 60)
    
    # First check if Ollama is running
    if not check_ollama_status():
        exit(1)
    
    print()
    
    # Test streaming
    success = test_ollama_streaming()
    
    if success:
        print("\n🎉 All tests passed! Ollama streaming is working.")
    else:
        print("\n❌ Tests failed. Check the output above for details.")
        exit(1) 