#!/usr/bin/env python3
"""
Simplified system verification test
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_basic_imports():
    """Test basic system imports"""
    print("Testing basic imports...")
    
    try:
        # Core utilities
        from utils.config import config
        from utils.logger import logger
        from utils.errors import AuctionBotError
        print("✓ Core utilities imported")
        
        # Basic AI components
        from ai.obd2_analysis import OBD2Analyzer
        from ai.dashboard_lights import DashboardLightAnalyzer
        from ai.filtering import VehicleFilteringEngine
        print("✓ AI components imported")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("Testing configuration...")
    
    try:
        from utils.config import config
        
        # Test basic config access
        system_name = config.get('system.name')
        platforms = config.get('platforms')
        
        if system_name and platforms:
            print("✓ Configuration loaded successfully")
            print(f"  System: {system_name}")
            print(f"  Platforms: {list(platforms.keys())}")
            return True
        else:
            print("✗ Configuration incomplete")
            return False
            
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_ai_analysis():
    """Test AI analysis components"""
    print("Testing AI analysis...")
    
    try:
        from ai.obd2_analysis import OBD2Analyzer
        from ai.dashboard_lights import DashboardLightAnalyzer
        from ai.filtering import VehicleFilteringEngine
        
        # Test OBD2 analyzer
        obd2_analyzer = OBD2Analyzer()
        test_codes = ['P0420', 'P0700']
        analysis = obd2_analyzer.analyze_obd2_codes(test_codes)
        
        if analysis and 'overall_assessment' in analysis:
            print("✓ OBD2 analyzer working")
            print(f"  Test analysis: {analysis['overall_assessment']}")
        else:
            print("✗ OBD2 analyzer failed")
            return False
        
        # Test dashboard analyzer
        dashboard_analyzer = DashboardLightAnalyzer()
        test_lights = ['check_engine', 'abs']
        light_analysis = dashboard_analyzer.analyze_dashboard_lights(test_lights)
        
        if light_analysis and 'overall_assessment' in light_analysis:
            print("✓ Dashboard analyzer working")
            print(f"  Test analysis: {light_analysis['overall_assessment']}")
        else:
            print("✗ Dashboard analyzer failed")
            return False
        
        # Test filtering engine
        filtering_engine = VehicleFilteringEngine()
        test_vehicle = {
            'vin': 'TEST123456789',
            'year': 2020,
            'make': 'Honda',
            'model': 'Accord',
            'mileage': 50000,
            'current_bid': 20000
        }
        
        evaluation = filtering_engine.evaluate_vehicle(test_vehicle)
        
        if evaluation and 'overall_score' in evaluation:
            print("✓ Filtering engine working")
            print(f"  Test vehicle score: {evaluation['overall_score']:.1f}")
            print(f"  Recommendation: {evaluation['recommendation']}")
            return True
        else:
            print("✗ Filtering engine failed")
            return False
            
    except Exception as e:
        print(f"✗ AI analysis test failed: {e}")
        return False

def test_user_criteria():
    """Test user criteria implementation"""
    print("Testing user criteria implementation...")
    
    try:
        from ai.obd2_analysis import OBD2Analyzer
        from ai.dashboard_lights import DashboardLightAnalyzer
        
        # Test transmission code detection (user avoids)
        obd2_analyzer = OBD2Analyzer()
        transmission_codes = ['P0700', 'P0750']  # Transmission codes
        compliance = obd2_analyzer.check_user_criteria_compliance(transmission_codes)
        
        if not compliance['meets_criteria'] and 'Transmission codes detected' in compliance['violations']:
            print("✓ Transmission code avoidance working")
        else:
            print("✗ Transmission code detection failed")
            return False
        
        # Test headlight warning detection (user avoids)
        dashboard_analyzer = DashboardLightAnalyzer()
        headlight_warnings = ['headlight_out']
        compliance = dashboard_analyzer.check_user_criteria_compliance(headlight_warnings)
        
        if not compliance['meets_criteria'] and 'Headlight warning lights detected' in compliance['violations']:
            print("✓ Headlight warning detection working")
        else:
            print("✗ Headlight warning detection failed")
            return False
        
        print("✓ User criteria implementation verified")
        return True
        
    except Exception as e:
        print(f"✗ User criteria test failed: {e}")
        return False

def main():
    """Run simplified tests"""
    print("AUCTION AUTOMATION SYSTEM - SIMPLIFIED VERIFICATION")
    print("=" * 55)
    
    tests = [
        test_basic_imports,
        test_configuration,
        test_ai_analysis,
        test_user_criteria
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            print()
    
    print("=" * 55)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ Core system verification PASSED!")
        print("\nThe auction automation system is ready for use.")
        print("\nNext steps:")
        print("1. Edit .env file with your credentials")
        print("2. Run: ./run.sh start")
        print("\nNote: Some advanced features may require additional setup")
        return 0
    else:
        print("✗ System verification FAILED - Check errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
