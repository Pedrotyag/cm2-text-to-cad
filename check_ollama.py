#!/usr/bin/env python3
"""
Quick Ollama Setup Checker
Run this to verify your Ollama configuration before starting CM²
"""

import os
import requests
from dotenv import load_dotenv

def check_ollama_setup():
    """Check Ollama setup and configuration"""
    print("🔍 Checking Ollama Setup...")
    print("=" * 50)
    
    # Load .env file
    load_dotenv()
    
    # Check environment variables
    llm_provider = os.getenv("LLM_PROVIDER", "").lower()
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "")
    ollama_timeout = os.getenv("OLLAMA_TIMEOUT", "600")
    
    print(f"📋 Configuration:")
    print(f"   LLM_PROVIDER: {llm_provider}")
    print(f"   OLLAMA_BASE_URL: {ollama_url}")
    print(f"   OLLAMA_MODEL: {ollama_model}")
    print(f"   OLLAMA_TIMEOUT: {ollama_timeout} seconds ({int(ollama_timeout)//60} minutes)")
    print()
    
    # Check if Ollama is configured
    if llm_provider != "ollama":
        print("⚠️  LLM_PROVIDER is not set to 'ollama'")
        print("   Set LLM_PROVIDER=ollama in your .env file")
        return False
    
    if not ollama_model:
        print("❌ OLLAMA_MODEL is not configured")
        print("   Set OLLAMA_MODEL in your .env file")
        print("   Example: OLLAMA_MODEL=hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M")
        return False
    
    # Check timeout configuration
    try:
        timeout_val = int(ollama_timeout)
        if timeout_val < 60:
            print("⚠️  OLLAMA_TIMEOUT is very low (less than 1 minute)")
            print("   Consider increasing it for better reliability")
        elif timeout_val > 1800:
            print("⚠️  OLLAMA_TIMEOUT is very high (more than 30 minutes)")
            print("   This might cause long waits if the model fails")
        else:
            print(f"✅ Timeout configuration looks reasonable ({timeout_val//60} minutes)")
    except ValueError:
        print("⚠️  OLLAMA_TIMEOUT is not a valid number")
        print("   Set OLLAMA_TIMEOUT to number of seconds (e.g., 600 for 10 minutes)")
    
    # Check if Ollama service is running
    try:
        print(f"🌐 Checking Ollama service at {ollama_url}...")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        
        if response.status_code != 200:
            print(f"❌ Ollama service not responding (status: {response.status_code})")
            print("   Start Ollama with: ollama serve")
            return False
        
        print("✅ Ollama service is running")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("   Start Ollama with: ollama serve")
        return False
    
    # Check available models
    try:
        models_data = response.json()
        available_models = [model.get('name', '') for model in models_data.get('models', [])]
        
        print(f"📦 Available models: {available_models}")
        
        if ollama_model in available_models:
            print(f"✅ Configured model '{ollama_model}' is available")
        else:
            print(f"❌ Configured model '{ollama_model}' not found")
            print(f"   Install it with: ollama pull {ollama_model}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return False
    
    print()
    print("🎉 Ollama setup looks good!")
    print("   You can now start CM² with: python main.py")
    print(f"   Expected response time: up to {int(ollama_timeout)//60} minutes per request")
    return True

def show_setup_instructions():
    """Show setup instructions"""
    print()
    print("🛠️  Ollama Setup Instructions:")
    print("=" * 50)
    print("1. Install Ollama:")
    print("   Visit: https://ollama.ai/")
    print()
    print("2. Start Ollama service:")
    print("   ollama serve")
    print()
    print("3. Pull the DeepSeek model:")
    print("   ollama pull hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M")
    print()
    print("4. Configure .env file:")
    print("   LLM_PROVIDER=ollama")
    print("   OLLAMA_BASE_URL=http://localhost:11434")
    print("   OLLAMA_MODEL=hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M")
    print()
    print("5. Run this script again to verify:")
    print("   python check_ollama.py")

if __name__ == "__main__":
    success = check_ollama_setup()
    
    if not success:
        show_setup_instructions()
        exit(1)
    else:
        print("Ready to use Ollama with CM²! 🚀") 