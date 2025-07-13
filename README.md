
# CarMax/Manheim Auction Automation System

A comprehensive, AI-powered vehicle auction automation system that discovers, analyzes, and evaluates vehicles from CarMax and Manheim auction platforms based on your specific criteria.

## Features

### 🚗 Multi-Platform Support
- **CarMax Auctions**: Automated bidding platform integration
- **Manheim Auctions**: Professional dealer auction access
- Stealth browser automation with anti-detection capabilities

### 🔍 Comprehensive Vehicle Analysis
- **Vehicle History**: Carfax and AutoCheck integration
- **Market Analysis**: CarGurus and DealersLink pricing data
- **AI Image Analysis**: Damage detection and condition assessment
- **OBD2 Code Analysis**: Diagnostic trouble code interpretation
- **Dashboard Light Analysis**: Warning light evaluation

### 🧠 Intelligent Filtering
- User-defined criteria enforcement
- AI-powered vehicle scoring
- Automated bid recommendations
- Risk assessment and profit analysis

### 📊 Data Integration
- Real-time market pricing
- Historical vehicle data
- Condition reports and inspections
- Comprehensive vehicle valuations

## Quick Start

### 1. System Setup
```bash
# Clone and setup the system
cd ~/auction_automation_system
chmod +x run.sh
./run.sh setup
```

### 2. Configuration
```bash
# Copy and edit environment variables
cp .env.example .env
nano .env
```

Add your credentials:
```env
# Platform Credentials
CARMAX_USERNAME=your_carmax_username
CARMAX_PASSWORD=your_carmax_password
MANHEIM_USERNAME=your_manheim_username
MANHEIM_PASSWORD=your_manheim_password

# API Keys (optional but recommended)
CARFAX_API_KEY=your_carfax_api_key
AUTOCHECK_API_KEY=your_autocheck_api_key
DEALERSLINK_API_KEY=your_dealerslink_api_key
```

### 3. Run the System
```bash
# Start with default settings
./run.sh start

# Or with custom criteria
./run.sh start --platforms carmax --max-price 30000 --max-mileage 100000
```

### 4. Monitor Progress
```bash
# Check status
./run.sh status

# View logs
./run.sh logs

# Stop the system
./run.sh stop
```

## User Criteria Implementation

The system implements your specific vehicle criteria:

### ❌ Avoid Criteria
- Vehicles with transmission flushes
- Major electrical issues
- Major transmission issues  
- Major engine issues
- Non-working headlights

### ✅ Prefer Criteria
- Vehicles needing minor paint work
- Vehicles needing minor body work
- Working headlights
- OBD2 inspection ready vehicles

### 📏 Specifications
- Price range: $5,000 - $50,000
- Maximum mileage: 150,000 miles
- Minimum year: 2015

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   CarMax API    │    │  Manheim API    │
│   & Scraping    │    │   & Scraping    │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │  Vehicle Discovery    │
         │     & Extraction      │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │   Data Integration    │
         │ Carfax│AutoCheck│etc  │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │   AI Analysis Engine  │
         │ Images│OBD2│Dashboard │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │ Intelligent Filtering │
         │   & Recommendations   │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │   Results Export      │
         │   JSON │ CSV │ TXT    │
         └───────────────────────┘
```

## Advanced Usage

### Custom Search Criteria
```bash
# Search specific platforms with custom criteria
./run.sh start \
  --platforms carmax manheim \
  --max-price 40000 \
  --max-mileage 120000 \
  --min-year 2018
```

### Configuration Customization
Edit `config/config.yaml` to customize:
- Rate limiting settings
- AI analysis parameters
- Integration endpoints
- Filtering criteria weights

### API Integration
The system supports official APIs when available:
- **Manheim MMR API**: Real-time market valuations
- **Carfax API**: Official vehicle history reports
- **AutoCheck API**: Comprehensive vehicle scoring
- **DealersLink API**: Professional appraisals

## Output Formats

### JSON Results
```json
{
  "vehicles_found": 150,
  "vehicles_analyzed": 150,
  "recommended_vehicles": 12,
  "results": [
    {
      "vin": "1HGBH41JXMN109186",
      "year": 2021,
      "make": "Honda",
      "model": "Accord",
      "current_bid": 18500,
      "evaluation": {
        "overall_score": 87.5,
        "recommendation": "strong_buy",
        "bid_recommendation": {
          "should_bid": true,
          "max_bid": 20000,
          "confidence": "high"
        }
      }
    }
  ]
}
```

### CSV Export
Includes key fields for spreadsheet analysis:
- VIN, Make, Model, Year, Mileage
- Current Bid, Recommended Max Bid
- Overall Score, Recommendation
- Platform, Location, Source URL

### Summary Report
Human-readable analysis with:
- Top vehicle recommendations
- Common issues found
- Market insights
- Bidding strategies

## Security Features

### Anti-Detection
- Residential proxy rotation
- Human-like browsing patterns
- Canvas fingerprint randomization
- User agent rotation
- Session persistence

### Data Protection
- Encrypted credential storage
- Secure session management
- Local data processing
- Optional cloud backup

## Monitoring & Logging

### Real-time Monitoring
```bash
# Watch live logs
tail -f logs/auction_bot.log

# Check system status
./run.sh status
```

### Performance Metrics
- Vehicles processed per hour
- Success rates by platform
- API response times
- Error tracking and recovery

## Troubleshooting

### Common Issues

**Login Required**
```bash
# Manual login may be needed for initial setup
# The system will prompt when authentication is required
```

**Rate Limiting**
```bash
# Adjust rate limits in config/config.yaml
# The system automatically handles rate limiting
```

**Missing Dependencies**
```bash
# Reinstall dependencies
./run.sh setup
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
./run.sh start
```

## Legal & Compliance

- ✅ Respects robots.txt and rate limits
- ✅ Uses official APIs when available
- ✅ Implements proper session management
- ✅ Follows platform terms of service
- ✅ Designed for authorized dealer accounts

## Support

### System Requirements
- Python 3.8+
- 4GB RAM minimum
- 10GB storage space
- Stable internet connection

### Browser Requirements
- Chromium/Chrome (auto-installed)
- Firefox (auto-installed)
- WebKit (auto-installed)

### Platform Access
- Valid CarMax dealer account
- Valid Manheim dealer account
- API keys for external services (optional)

## Updates & Maintenance

The system includes:
- Automatic dependency updates
- Browser version management
- Configuration validation
- Error recovery mechanisms
- Performance optimization

---

**Note**: This system is designed for authorized automotive dealers with legitimate access to auction platforms. Ensure compliance with all platform terms of service and applicable laws.
