#!/usr/bin/env python3
"""
System verification test for the auction automation system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all critical imports"""
    print("Testing imports...")
    
    try:
        # Core system imports
        from utils.config import config
        from utils.logger import logger
        from utils.errors import AuctionBotError
        from utils.rate_limiter import rate_limiter
        
        # Automation imports
        from automation.browser import StealthBrowser
        
        # Scraper imports
        from scrapers.carmax import CarMaxScraper
        from scrapers.manheim import ManheimScraper
        
        # Integration imports
        from integrations.carfax import CarfaxIntegrator
        from integrations.autocheck import AutoCheckIntegrator
        from integrations.dealerslink import DealersLinkIntegrator
        from integrations.cargurus import CarGurusIntegrator
        
        # AI imports
        from ai.image_analysis import VehicleImageAnalyzer
        from ai.obd2_analysis import OBD2Analyzer
        from ai.dashboard_lights import DashboardLightAnalyzer
        from ai.filtering import VehicleFilteringEngine
        
        # Main orchestrator
        from main import AuctionAutomationOrchestrator
        
        print("✓ All imports successful")
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

def test_ai_components():
    """Test AI component initialization"""
    print("Testing AI components...")
    
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
        else:
            print("✗ OBD2 analyzer failed")
            return False
        
        # Test dashboard analyzer
        dashboard_analyzer = DashboardLightAnalyzer()
        test_lights = ['check_engine', 'abs']
        light_analysis = dashboard_analyzer.analyze_dashboard_lights(test_lights)
        
        if light_analysis and 'overall_assessment' in light_analysis:
            print("✓ Dashboard analyzer working")
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
            return True
        else:
            print("✗ Filtering engine failed")
            return False
            
    except Exception as e:
        print(f"✗ AI component test failed: {e}")
        return False

def test_system_integration():
    """Test system integration"""
    print("Testing system integration...")
    
    try:
        from main import AuctionAutomationOrchestrator
        
        # Initialize orchestrator
        orchestrator = AuctionAutomationOrchestrator()
        
        if orchestrator.filtering_engine and orchestrator.integrations:
            print("✓ System orchestrator initialized")
            print(f"  Integrations loaded: {len(orchestrator.integrations)}")
            print(f"  AI analyzers loaded: {len(orchestrator.ai_analyzers)}")
            return True
        else:
            print("✗ System orchestrator failed")
            return False
            
    except Exception as e:
        print(f"✗ System integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("AUCTION AUTOMATION SYSTEM - VERIFICATION TEST")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_ai_components,
        test_system_integration
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
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ System verification PASSED - Ready for use!")
        print("\nNext steps:")
        print("1. Edit .env file with your credentials")
        print("2. Run: ./run.sh start")
        return 0
    else:
        print("✗ System verification FAILED - Check errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
