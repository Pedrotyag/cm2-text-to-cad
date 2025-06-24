# Ollama Integration Setup

## Overview

The CM² Text-to-CAD system now supports local AI models through Ollama, allowing you to run the system completely offline without needing external API keys.

## Prerequisites

1. **Install Ollama**
   - Visit [https://ollama.ai/](https://ollama.ai/)
   - Download and install for your operating system
   - Make sure Ollama is running: `ollama serve`

2. **Pull the DeepSeek Model**
   ```bash
   ollama pull hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M
   ```

## Configuration

1. **Create or modify your `.env` file:**
   ```env
   # Choose LLM provider
   LLM_PROVIDER=ollama
   
   # Ollama settings
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M
   OLLAMA_TIMEOUT=600  # 10 minutes (adjust based on your model/hardware)
   
   # Gemini API key not needed when using Ollama
   # GEMINI_API_KEY=your_api_key_here
   ```

2. **Timeout Configuration:**
   Local models can take significant time to respond. Adjust timeout based on your setup:
   ```env
   # Recommended timeouts by model size:
   OLLAMA_TIMEOUT=300   # 5 minutes  - Small models (7B)
   OLLAMA_TIMEOUT=600   # 10 minutes - Medium models (8B-13B) [DEFAULT]
   OLLAMA_TIMEOUT=1200  # 20 minutes - Large models (30B+)
   OLLAMA_TIMEOUT=1800  # 30 minutes - Very large models
   ```

3. **Alternative models (if available in Ollama):**
   ```env
   # Other model options you can try:
   OLLAMA_MODEL=llama2:7b
   OLLAMA_MODEL=codellama:7b
   OLLAMA_MODEL=mistral:7b
   ```

## Usage

1. **Start Ollama service:**
   ```bash
   ollama serve
   ```

2. **Start the CM² application:**
   ```bash
   python main.py
   ```

3. **The system will automatically:**
   - Detect that Ollama is configured
   - Connect to the local Ollama server
   - Use the specified model for CAD generation
   - Show timeout information in logs

## Features with Ollama

- ✅ **Complete offline operation** - No internet required after setup
- ✅ **Privacy** - All data stays on your machine
- ✅ **Customizable models** - Use any model available in Ollama
- ✅ **Same CAD capabilities** - Full CadQuery support
- ✅ **Edit features** - All editing capabilities work with Ollama
- ✅ **Configurable timeouts** - Adjust for your hardware and model size

## Model Performance Notes

- **DeepSeek-R1-0528-Qwen3-8B** is recommended for CAD tasks
- Larger models (13B+) may provide better results but require more RAM and time
- Q4_K_M quantization provides good balance of quality and speed
- Response times will vary based on your hardware (CPU/GPU/RAM)
- First response may be slower as the model loads into memory

## Performance Optimization

### Hardware Recommendations:
- **CPU**: Modern multi-core processor (8+ cores recommended)
- **RAM**: 16GB+ for 8B models, 32GB+ for larger models
- **Storage**: SSD for faster model loading
- **GPU**: Optional but significantly speeds up inference if supported

### Ollama Performance Settings:
```bash
# Set environment variables before starting Ollama
export OLLAMA_NUM_PARALLEL=1      # Number of parallel requests
export OLLAMA_MAX_LOADED_MODELS=1 # Keep only one model in memory
export OLLAMA_HOST=0.0.0.0        # Allow external connections
```

## Troubleshooting

### Timeout Issues
If you're getting timeout errors:

1. **Increase timeout in `.env`:**
   ```env
   OLLAMA_TIMEOUT=1200  # 20 minutes
   ```

2. **Use a smaller/faster model:**
   ```bash
   ollama pull llama2:7b
   ```
   ```env
   OLLAMA_MODEL=llama2:7b
   OLLAMA_TIMEOUT=300
   ```

3. **Check system resources:**
   ```bash
   # Monitor CPU and RAM usage
   htop
   
   # Check if model is loaded
   ollama ps
   ```

### Connection Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check available models
ollama list
```

### Model Loading
```bash
# If model isn't found, pull it explicitly
ollama pull hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M

# Check model status
ollama show hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M
```

### Performance Optimization
```env
# Adjust Ollama settings in .env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=600

# Or use environment variables:
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=1
```

## Switching Between Providers

You can easily switch between Gemini and Ollama by changing the `LLM_PROVIDER` in your `.env` file:

```env
# Use Gemini (cloud)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key

# Use Ollama (local)
LLM_PROVIDER=ollama
OLLAMA_MODEL=hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M
OLLAMA_TIMEOUT=600
```

Restart the application after changing providers.

## Hardware Requirements

- **Minimum:** 8GB RAM, modern CPU, 5-10 minutes response time
- **Recommended:** 16GB+ RAM, multi-core CPU, 2-5 minutes response time
- **Optimal:** 32GB+ RAM, GPU acceleration, <2 minutes response time

## Support

If you encounter issues with Ollama integration, check:
1. Ollama service is running (`ollama serve`)
2. Model is downloaded (`ollama list`)
3. Correct model name in `.env` file
4. Sufficient timeout configured (`OLLAMA_TIMEOUT`)
5. Check logs for specific error messages 