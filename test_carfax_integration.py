#!/usr/bin/env python3
"""
Test script for the updated CARFAX integration
Tests both the new wrapper API approach and fallback methods
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from integrations.carfax import CarfaxIntegrator, CarfaxServiceHistory
from utils.logger import logger

def test_carfax_service_history_class():
    """Test the CarfaxServiceHistory class directly"""
    print("\n=== Testing CarfaxServiceHistory Class ===")
    
    # Test VIN validation
    try:
        CarfaxServiceHistory.get("INVALID_VIN")
        print("❌ VIN validation failed - should have raised ValueError")
    except ValueError as e:
        print(f"✅ VIN validation working: {e}")
    except Exception as e:
        print(f"❌ Unexpected error in VIN validation: {e}")
    
    # Test credential validation
    try:
        CarfaxServiceHistory.get("1G1GCCBX3JX001788")
        print("❌ Credential validation failed - should have raised RuntimeError")
    except RuntimeError as e:
        print(f"✅ Credential validation working: {e}")
    except Exception as e:
        print(f"❌ Unexpected error in credential validation: {e}")
    
    # Test with mock credentials (will fail API call but test structure)
    try:
        CarfaxServiceHistory.set_product_data_id("1234567890123456")  # 16 chars
        CarfaxServiceHistory.set_location_id("TEST_LOC")
        
        result = CarfaxServiceHistory.get("1G1GCCBX3JX001788")
        print(f"✅ Mock API call completed, returned structure: {list(result.keys())}")
        
        # Verify response structure
        expected_keys = ['Decode', 'Overview', 'Records']
        if all(key in result for key in expected_keys):
            print("✅ Response structure is correct")
        else:
            print(f"❌ Response structure incorrect. Expected {expected_keys}, got {list(result.keys())}")
            
    except Exception as e:
        print(f"❌ Error testing with mock credentials: {e}")

def test_carfax_integrator():
    """Test the CarfaxIntegrator class"""
    print("\n=== Testing CarfaxIntegrator Class ===")
    
    try:
        # Initialize integrator
        integrator = CarfaxIntegrator()
        print("✅ CarfaxIntegrator initialized successfully")
        
        # Test VIN lookup (will use fallback methods since no real credentials)
        test_vin = "1G1GCCBX3JX001788"
        print(f"Testing VIN lookup for: {test_vin}")
        
        result = integrator.get_vehicle_history(test_vin)
        print(f"✅ Vehicle history lookup completed")
        print(f"   Result keys: {list(result.keys()) if result else 'Empty result'}")
        print(f"   Data source: {result.get('source', 'Unknown') if result else 'No data'}")
        
        # Test analysis if we got data
        if result:
            analysis = integrator.analyze_history_flags(result)
            print(f"✅ History analysis completed")
            print(f"   Overall risk: {analysis.get('overall_risk', 'Unknown')}")
            print(f"   Red flags: {len(analysis.get('red_flags', []))}")
            print(f"   Yellow flags: {len(analysis.get('yellow_flags', []))}")
            print(f"   Green flags: {len(analysis.get('green_flags', []))}")
        
        # Clean up
        integrator.close()
        print("✅ Integrator closed successfully")
        
    except Exception as e:
        print(f"❌ Error testing CarfaxIntegrator: {e}")
        import traceback
        traceback.print_exc()

def test_configuration():
    """Test configuration loading"""
    print("\n=== Testing Configuration ===")
    
    try:
        from utils.config import config
        
        carfax_config = config.get_integration_config('carfax')
        print(f"✅ Configuration loaded successfully")
        print(f"   Enabled: {carfax_config.get('enabled', False)}")
        print(f"   Use wrapper API: {carfax_config.get('use_wrapper_api', False)}")
        print(f"   Fallback scraping: {carfax_config.get('fallback_scraping', False)}")
        print(f"   Has product_data_id: {'product_data_id' in carfax_config}")
        print(f"   Has location_id: {'location_id' in carfax_config}")
        print(f"   Has legacy api_key: {'api_key' in carfax_config}")
        
    except Exception as e:
        print(f"❌ Error testing configuration: {e}")

def test_environment_variables():
    """Test environment variable setup"""
    print("\n=== Testing Environment Variables ===")
    
    env_vars = [
        'CARFAX_PRODUCT_DATA_ID',
        'CARFAX_LOCATION_ID', 
        'CARFAX_API_KEY'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set (length: {len(value)})")
        else:
            print(f"⚠️  {var}: Not set")

def main():
    """Run all tests"""
    print("🚗 CARFAX Integration Test Suite")
    print("=" * 50)
    
    # Test environment variables
    test_environment_variables()
    
    # Test configuration
    test_configuration()
    
    # Test CarfaxServiceHistory class
    test_carfax_service_history_class()
    
    # Test CarfaxIntegrator
    test_carfax_integrator()
    
    print("\n" + "=" * 50)
    print("🏁 Test suite completed!")
    print("\nNOTE: To fully test the CARFAX wrapper API functionality,")
    print("you need to set the following environment variables:")
    print("- CARFAX_PRODUCT_DATA_ID (16-character Product Data ID)")
    print("- CARFAX_LOCATION_ID (Location ID from CARFAX)")
    print("\nThese require a CARFAX Service Data Transfer Facilitation Agreement.")

if __name__ == "__main__":
    main()
