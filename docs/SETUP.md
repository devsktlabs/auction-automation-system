
# CarMax AI Agent Setup Guide

This guide will help you set up and configure the CarMax AI Agent for local vehicle analysis.

## Prerequisites

- Python 3.8 or higher
- Ubuntu/Linux system (recommended)
- At least 8GB RAM (16GB+ recommended for vision models)
- GPU with CUDA support (optional but recommended)

## Installation Steps

### 1. System Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y python3-pip python3-venv git curl wget

# Install Chrome/Chromium for web scraping
sudo apt install -y chromium-browser

# Optional: Install CUDA for GPU acceleration
# Follow NVIDIA CUDA installation guide for your system
```

### 2. Python Environment Setup

```bash
# Navigate to the auction automation system directory
cd /home/ubuntu/auction_automation_system

# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install additional AI agent dependencies
pip install pdfplumber pypdf2 ollama-python transformers torch torchvision pillow opencv-python
```

### 3. Ollama Setup (Local LLM)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve &

# Pull recommended models
ollama pull llama3.2
ollama pull llama3.2:1b  # Smaller model for faster inference

# Test Ollama installation
ollama list
```

### 4. Vision Models Setup

The system will automatically download vision models on first use. To pre-download:

```python
# Run this Python script to pre-download models
python3 -c "
from transformers import BlipProcessor, BlipForConditionalGeneration
print('Downloading BLIP model...')
processor = BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base')
model = BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')
print('BLIP model downloaded successfully!')
"
```

### 5. Configuration

Create or update the configuration file:

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

Add the following configuration:

```env
# CarMax AI Agent Configuration
CARMAX_AI_OUTPUT_DIR=./data/carmax_analysis
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
VISION_MODEL=blip
DEVICE=auto  # auto, cpu, cuda, mps

# Rate limiting
REQUESTS_PER_MINUTE=30
MAX_CONCURRENT_ANALYSES=3

# Image processing
MAX_IMAGES_PER_VEHICLE=20
IMAGE_DOWNLOAD_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/carmax_ai_agent.log
```

### 6. Directory Structure

The agent will create the following directory structure:

```
auction_automation_system/
├── agents/
│   ├── carmax_ai_agent.py
│   ├── vision.py
│   ├── autocheck.py
│   └── note_gen.py
├── data/
│   └── carmax_analysis/
│       ├── images/
│       └── reports/
├── tests/
│   └── test_carmax_ai_agent.py
└── docs/
    └── SETUP.md
```

## Usage Examples

### Basic Usage

```python
import asyncio
from agents.carmax_ai_agent import CarMaxAIAgent

async def analyze_vehicle():
    agent = CarMaxAIAgent()
    
    # Analyze a single vehicle
    url = "https://carmaxauctions.com/vehicle/12345"
    result = await agent.analyze_vehicle(url)
    
    print(f"Condition Score: {result.condition_score}")
    print(f"Recommendation: {result.recommendation}")
    print(f"Red Flags: {result.red_flags}")

# Run the analysis
asyncio.run(analyze_vehicle())
```

### Batch Processing

```python
import asyncio
from agents.carmax_ai_agent import CarMaxAIAgent

async def batch_analyze():
    agent = CarMaxAIAgent()
    
    # List of vehicle URLs
    urls = [
        "https://carmaxauctions.com/vehicle/12345",
        "https://carmaxauctions.com/vehicle/12346",
        "https://carmaxauctions.com/vehicle/12347"
    ]
    
    # Analyze multiple vehicles
    results = await agent.batch_analyze(urls, max_concurrent=2)
    
    for result in results:
        print(f"Vehicle: {result.vehicle_data.make} {result.vehicle_data.model}")
        print(f"Score: {result.condition_score}")
        print(f"Recommendation: {result.recommendation}")
        print("---")

asyncio.run(batch_analyze())
```

### Integration with Existing System

```python
# Add to your existing main.py
from agents.carmax_ai_agent import CarMaxAIAgent

class AuctionAutomationOrchestrator:
    def __init__(self):
        # ... existing initialization ...
        self.carmax_ai_agent = CarMaxAIAgent()
    
    async def analyze_carmax_vehicle(self, url):
        """Analyze CarMax vehicle with AI agent"""
        try:
            result = await self.carmax_ai_agent.analyze_vehicle(url)
            
            # Save to your existing database/storage
            self.save_analysis_result(result)
            
            return result
        except Exception as e:
            logger.error(f"CarMax AI analysis failed: {e}")
            return None
```

## Testing

Run the test suite to verify installation:

```bash
# Run basic tests
python3 tests/test_carmax_ai_agent.py

# Run with pytest (if installed)
pip install pytest pytest-asyncio
pytest tests/test_carmax_ai_agent.py -v
```

## Troubleshooting

### Common Issues

1. **Ollama Connection Error**
   ```bash
   # Check if Ollama is running
   ps aux | grep ollama
   
   # Start Ollama if not running
   ollama serve &
   
   # Test connection
   curl http://localhost:11434/api/tags
   ```

2. **Vision Model Download Issues**
   ```bash
   # Clear Hugging Face cache
   rm -rf ~/.cache/huggingface/
   
   # Re-download models
   python3 -c "from transformers import BlipProcessor; BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base')"
   ```

3. **Chrome Driver Issues**
   ```bash
   # Install Chrome driver manually
   sudo apt install -y chromium-chromedriver
   
   # Or use the automatic installer
   pip install --upgrade undetected-chromedriver
   ```

4. **Memory Issues**
   ```bash
   # Use smaller models
   export OLLAMA_MODEL=llama3.2:1b
   export VISION_MODEL=blip-base
   
   # Reduce batch size
   export MAX_CONCURRENT_ANALYSES=1
   ```

### Performance Optimization

1. **GPU Acceleration**
   ```bash
   # Install CUDA-enabled PyTorch
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   
   # Verify GPU availability
   python3 -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Model Caching**
   ```bash
   # Pre-download all models to avoid delays
   python3 -c "
   from agents.vision import VehicleVisionAnalyzer
   analyzer = VehicleVisionAnalyzer()
   analyzer._load_models()
   print('All models cached successfully!')
   "
   ```

3. **Rate Limiting**
   - Adjust `REQUESTS_PER_MINUTE` in configuration
   - Use residential proxies for higher limits
   - Implement request queuing for large batches

## Security Considerations

1. **Authentication**
   - Store CarMax credentials securely
   - Use environment variables for sensitive data
   - Implement session management

2. **Rate Limiting**
   - Respect website terms of service
   - Implement exponential backoff
   - Monitor for IP blocking

3. **Data Privacy**
   - Encrypt stored vehicle data
   - Implement data retention policies
   - Secure API endpoints

## Monitoring and Logging

1. **Log Configuration**
   ```python
   # Configure detailed logging
   import logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('carmax_ai_agent.log'),
           logging.StreamHandler()
       ]
   )
   ```

2. **Performance Metrics**
   - Track analysis completion times
   - Monitor model inference speeds
   - Log error rates and types

3. **Health Checks**
   ```bash
   # Create health check script
   python3 -c "
   from agents.carmax_ai_agent import CarMaxAIAgent
   agent = CarMaxAIAgent()
   print('✓ Agent initialized successfully')
   print('✓ All components healthy')
   "
   ```

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the test output for specific errors
3. Check system logs: `tail -f logs/carmax_ai_agent.log`
4. Verify all dependencies are installed correctly

## Next Steps

1. **Customize Analysis**: Modify the analysis parameters in `agents/carmax_ai_agent.py`
2. **Add Features**: Extend the vision analysis or add new data sources
3. **Scale Up**: Implement distributed processing for large-scale analysis
4. **Integration**: Connect with your existing auction automation workflows

The CarMax AI Agent is now ready for use! Start with single vehicle analysis to verify everything works correctly, then scale up to batch processing as needed.
