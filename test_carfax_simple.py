#!/usr/bin/env python3
"""
Simple test script for the CARFAX Service History wrapper
Tests only the core wrapper functionality without browser dependencies
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test just the CarfaxServiceHistory class without browser dependencies
def test_carfax_service_history_standalone():
    """Test the CarfaxServiceHistory class directly"""
    print("🚗 Testing CARFAX Service History Wrapper")
    print("=" * 50)
    
    # Import only what we need
    import requests
    import re
    import json
    from typing import Dict, Optional, List, Union
    
    # Copy the CarfaxServiceHistory class here for standalone testing
    class CarfaxServiceHistory:
        """
        Python implementation of CARFAX Service History API wrapper
        Based on the amattu2/CARFAX-Wrapper PHP implementation
        """
        
        # CARFAX Service History API endpoint
        _endpoint = "https://servicesocket.carfax.com/data/1"
        _product_data_id = None
        _location_id = None
        
        @classmethod
        def set_location_id(cls, location_id: str) -> None:
            """Set the CARFAX Location ID (provided during account setup)"""
            if not location_id or not isinstance(location_id, str):
                raise ValueError("Location ID must be a non-empty string")
            if len(location_id) < 1 or len(location_id) > 50:
                raise ValueError("Location ID must be between 1 and 50 characters")
            cls._location_id = location_id
        
        @classmethod
        def set_product_data_id(cls, product_data_id: str) -> None:
            """Set the CARFAX Product Data ID (API key equivalent)"""
            if not product_data_id or not isinstance(product_data_id, str):
                raise ValueError("Product Data ID must be a non-empty string")
            if len(product_data_id) != 16:
                raise ValueError("Product Data ID must be exactly 16 characters")
            cls._product_data_id = product_data_id
        
        @classmethod
        def get(cls, vin: str) -> Dict[str, Union[str, int, List, Dict]]:
            """Fetch vehicle history by VIN"""
            # Validate VIN format
            if not vin or not isinstance(vin, str):
                raise ValueError("VIN must be a non-empty string")
            
            vin = vin.upper().strip()
            if not re.match(r'^[A-Z0-9]{17}$', vin):
                raise ValueError("VIN must be exactly 17 alphanumeric characters")
            
            # Validate required credentials
            if not cls._product_data_id:
                raise RuntimeError("Product Data ID must be set before making requests")
            if not cls._location_id:
                raise RuntimeError("Location ID must be set before making requests")
            
            # Make API request
            response_data = cls._post({
                'productDataId': cls._product_data_id,
                'locationId': cls._location_id,
                'vin': vin
            })
            
            if not response_data:
                # Return empty formatted result if API fails
                return {
                    'Decode': {
                        'VIN': vin,
                        'Year': '',
                        'Make': '',
                        'Model': '',
                        'Trim': '',
                        'Driveline': ''
                    },
                    'Overview': [],
                    'Records': []
                }
            
            # Format and return the response
            return cls._format_response(response_data, vin)
        
        @classmethod
        def _post(cls, fields: Dict[str, str]) -> Optional[Dict]:
            """Submit POST request to CARFAX Service History API"""
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'CARFAX-Python-Wrapper/1.0'
                }
                
                response = requests.post(
                    cls._endpoint,
                    json=fields,
                    headers=headers,
                    timeout=10
                )
                
                # Check for HTTP errors
                if response.status_code != 200:
                    print(f"⚠️  CARFAX API returned status {response.status_code}")
                    return None
                
                # Parse JSON response
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    print("❌ Failed to parse CARFAX API response as JSON")
                    return None
                
                # Check for API error messages
                if 'errorMessages' in data and data['errorMessages']:
                    print(f"❌ CARFAX API error: {data['errorMessages']}")
                    return None
                
                # Validate service history data
                if 'serviceHistory' not in data or not isinstance(data['serviceHistory'], list):
                    print("⚠️  CARFAX API response missing or invalid serviceHistory")
                    return None
                
                return data
                
            except requests.RequestException as e:
                print(f"❌ CARFAX API request failed: {e}")
                return None
            except Exception as e:
                print(f"❌ Unexpected error in CARFAX API request: {e}")
                return None
        
        @classmethod
        def _format_response(cls, data: Dict, vin: str) -> Dict[str, Union[str, int, List, Dict]]:
            """Format API response to match expected structure"""
            result = {
                'Decode': {
                    'VIN': vin,
                    'Year': '',
                    'Make': '',
                    'Model': '',
                    'Trim': '',
                    'Driveline': ''
                },
                'Overview': [],
                'Records': []
            }
            
            try:
                service_history = data.get('serviceHistory', [])
                
                # Extract vehicle decode information from first record if available
                if service_history:
                    first_record = service_history[0]
                    result['Decode'].update({
                        'Year': str(first_record.get('year', '')),
                        'Make': first_record.get('make', ''),
                        'Model': first_record.get('model', ''),
                        'Trim': first_record.get('bodyTypeDescription', ''),
                        'Driveline': first_record.get('driveline', '')
                    })
                
                # Process service categories for overview
                service_categories = {}
                
                # Process detailed records
                for record in service_history:
                    # Extract record details
                    record_date = cls._parse_date(record.get('date'))
                    odometer = cls._parse_odometer(record.get('odometer'))
                    services = record.get('services', [])
                    record_type = record.get('type', 'Service')
                    
                    # Add to detailed records
                    result['Records'].append({
                        'Date': record_date,
                        'Odometer': odometer,
                        'Services': services if isinstance(services, list) else [str(services)],
                        'Type': record_type
                    })
                    
                    # Update service categories for overview
                    for service in services:
                        if isinstance(service, str):
                            service_name = service.strip()
                            if service_name:
                                if service_name not in service_categories:
                                    service_categories[service_name] = {
                                        'Name': service_name,
                                        'Date': record_date,
                                        'Odometer': odometer
                                    }
                                else:
                                    # Update with most recent occurrence
                                    if record_date and (not service_categories[service_name]['Date'] or 
                                                      record_date > service_categories[service_name]['Date']):
                                        service_categories[service_name]['Date'] = record_date
                                        service_categories[service_name]['Odometer'] = odometer
                
                # Convert service categories to overview list
                result['Overview'] = list(service_categories.values())
                
            except Exception as e:
                print(f"❌ Error formatting CARFAX response: {e}")
            
            return result
        
        @classmethod
        def _parse_date(cls, date_value) -> Optional[str]:
            """Parse date value, returning None for invalid dates"""
            if not date_value or date_value == "Not Reported":
                return None
            return str(date_value) if date_value else None
        
        @classmethod
        def _parse_odometer(cls, odometer_value) -> int:
            """Parse odometer value, returning 0 for invalid values"""
            if not odometer_value:
                return 0
            try:
                return int(odometer_value)
            except (ValueError, TypeError):
                return 0
    
    # Test VIN validation
    print("\n1. Testing VIN validation...")
    try:
        CarfaxServiceHistory.get("INVALID_VIN")
        print("❌ VIN validation failed - should have raised ValueError")
    except ValueError as e:
        print(f"✅ VIN validation working: {e}")
    except Exception as e:
        print(f"❌ Unexpected error in VIN validation: {e}")
    
    # Test credential validation
    print("\n2. Testing credential validation...")
    try:
        CarfaxServiceHistory.get("1G1GCCBX3JX001788")
        print("❌ Credential validation failed - should have raised RuntimeError")
    except RuntimeError as e:
        print(f"✅ Credential validation working: {e}")
    except Exception as e:
        print(f"❌ Unexpected error in credential validation: {e}")
    
    # Test with mock credentials (will fail API call but test structure)
    print("\n3. Testing with mock credentials...")
    try:
        CarfaxServiceHistory.set_product_data_id("1234567890123456")  # 16 chars
        CarfaxServiceHistory.set_location_id("TEST_LOC")
        
        result = CarfaxServiceHistory.get("1G1GCCBX3JX001788")
        print(f"✅ Mock API call completed, returned structure: {list(result.keys())}")
        
        # Verify response structure
        expected_keys = ['Decode', 'Overview', 'Records']
        if all(key in result for key in expected_keys):
            print("✅ Response structure is correct")
            
            # Check Decode structure
            decode = result['Decode']
            decode_keys = ['VIN', 'Year', 'Make', 'Model', 'Trim', 'Driveline']
            if all(key in decode for key in decode_keys):
                print("✅ Decode structure is correct")
            else:
                print(f"❌ Decode structure incorrect. Expected {decode_keys}, got {list(decode.keys())}")
        else:
            print(f"❌ Response structure incorrect. Expected {expected_keys}, got {list(result.keys())}")
            
    except Exception as e:
        print(f"❌ Error testing with mock credentials: {e}")
    
    # Test environment variables
    print("\n4. Testing environment variables...")
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
    
    # Test with real credentials if available
    product_data_id = os.getenv('CARFAX_PRODUCT_DATA_ID')
    location_id = os.getenv('CARFAX_LOCATION_ID')
    
    if product_data_id and location_id:
        print("\n5. Testing with real credentials...")
        try:
            CarfaxServiceHistory.set_product_data_id(product_data_id)
            CarfaxServiceHistory.set_location_id(location_id)
            
            test_vin = "1G1GCCBX3JX001788"
            print(f"   Testing VIN: {test_vin}")
            
            result = CarfaxServiceHistory.get(test_vin)
            
            if result and (result.get('Records') or result.get('Overview')):
                print("✅ Real API call successful!")
                print(f"   Vehicle: {result['Decode']['Year']} {result['Decode']['Make']} {result['Decode']['Model']}")
                print(f"   Overview items: {len(result['Overview'])}")
                print(f"   Records: {len(result['Records'])}")
                
                # Show sample data
                if result['Overview']:
                    print(f"   Sample service: {result['Overview'][0]['Name']}")
                if result['Records']:
                    print(f"   Sample record: {result['Records'][0]['Type']} - {len(result['Records'][0]['Services'])} services")
            else:
                print("⚠️  Real API call returned no data")
                
        except Exception as e:
            print(f"❌ Error testing with real credentials: {e}")
    else:
        print("\n5. Skipping real API test (credentials not available)")
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\nTo test with real CARFAX API:")
    print("1. Set CARFAX_PRODUCT_DATA_ID environment variable (16 characters)")
    print("2. Set CARFAX_LOCATION_ID environment variable")
    print("3. Ensure you have a CARFAX Service Data Transfer Facilitation Agreement")

if __name__ == "__main__":
    test_carfax_service_history_standalone()
