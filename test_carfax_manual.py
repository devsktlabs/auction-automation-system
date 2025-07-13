#!/usr/bin/env python3
"""
CARFAX Integration Manual Test Script

This script allows you to test the CARFAX dealer portal integration with specific VIN numbers.
It will prompt for credentials if not found in environment variables, run the scraping for each VIN,
display results in a readable format, and save detailed results to a JSON file.

Usage Examples:
    # Interactive mode - prompts for VINs one by one
    python test_carfax_manual.py

    # Test specific VINs from command line
    python test_carfax_manual.py --vins 1HGBH41JXMN109186 2HGBH41JXMN109187

    # Test with custom credentials (will prompt securely)
    python test_carfax_manual.py --prompt-credentials

    # Test with timeout override
    python test_carfax_manual.py --timeout 30

Requirements:
    - CARFAX dealer portal credentials (username/password)
    - Set environment variables CARFAX_DEALER_USERNAME and CARFAX_DEALER_PASSWORD
    - Or script will prompt for credentials securely

Environment Variables:
    CARFAX_DEALER_USERNAME - Your CARFAX dealer portal username
    CARFAX_DEALER_PASSWORD - Your CARFAX dealer portal password
"""

import argparse
import json
import os
import sys
import time
import getpass
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import traceback

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from integrations.carfax import CarfaxIntegrator, CarfaxDealerPortalScraper
    from utils.logger import logger
except ImportError as e:
    print(f"❌ Error importing CARFAX integration: {e}")
    print("Make sure you're running this script from the auction_automation_system directory")
    sys.exit(1)


class CarfaxTester:
    """Test harness for CARFAX integration"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.results = []
        self.integrator = None
        
    def get_credentials(self, prompt_override: bool = False) -> tuple:
        """Get CARFAX credentials from environment or prompt user"""
        username = os.getenv('CARFAX_DEALER_USERNAME')
        password = os.getenv('CARFAX_DEALER_PASSWORD')
        
        if not username or not password or prompt_override:
            print("\n🔐 CARFAX Dealer Portal Credentials Required")
            print("=" * 50)
            
            if not username or prompt_override:
                username = input("Enter CARFAX dealer username: ").strip()
                if not username:
                    raise ValueError("Username is required")
            
            if not password or prompt_override:
                password = getpass.getpass("Enter CARFAX dealer password: ").strip()
                if not password:
                    raise ValueError("Password is required")
            
            # Set environment variables for the session
            os.environ['CARFAX_DEALER_USERNAME'] = username
            os.environ['CARFAX_DEALER_PASSWORD'] = password
            
            print("✅ Credentials configured for this session")
        else:
            print("✅ Using credentials from environment variables")
            
        return username, password
    
    def validate_vin(self, vin: str) -> bool:
        """Validate VIN format"""
        vin = vin.upper().strip()
        if len(vin) != 17:
            return False
        
        # Basic VIN character validation
        valid_chars = set('ABCDEFGHJKLMNPRSTUVWXYZ0123456789')
        return all(c in valid_chars for c in vin)
    
    def get_vins_interactive(self) -> List[str]:
        """Get VINs from user input interactively"""
        vins = []
        print("\n🚗 Enter VIN Numbers to Test")
        print("=" * 30)
        print("Enter VINs one by one (press Enter with empty line to finish)")
        print("Example VIN: 1HGBH41JXMN109186")
        
        while True:
            vin = input(f"VIN #{len(vins) + 1}: ").strip().upper()
            
            if not vin:
                break
                
            if not self.validate_vin(vin):
                print(f"❌ Invalid VIN format: {vin}")
                print("VINs must be exactly 17 characters (letters and numbers)")
                continue
                
            if vin in vins:
                print(f"⚠️  VIN {vin} already added")
                continue
                
            vins.append(vin)
            print(f"✅ Added VIN: {vin}")
        
        return vins
    
    def test_single_vin(self, vin: str) -> Dict[str, Any]:
        """Test CARFAX lookup for a single VIN"""
        print(f"\n🔍 Testing VIN: {vin}")
        print("-" * 40)
        
        start_time = time.time()
        result = {
            'vin': vin,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'elapsed_seconds': 0,
            'data': None,
            'error': None,
            'flags_analysis': None
        }
        
        try:
            # Initialize integrator if not done
            if not self.integrator:
                self.integrator = CarfaxIntegrator()
            
            print("⏳ Fetching vehicle history...")
            
            # Get vehicle history
            history_data = self.integrator.get_vehicle_history(vin)
            
            if history_data and not history_data.get('error'):
                result['success'] = True
                result['data'] = history_data
                
                # Analyze flags
                print("🔍 Analyzing history for red flags...")
                flags_analysis = self.integrator.analyze_history_flags(history_data)
                result['flags_analysis'] = flags_analysis
                
                print("✅ Successfully retrieved vehicle history")
                self._display_summary(history_data, flags_analysis)
                
            else:
                result['error'] = history_data.get('error', 'No data returned')
                print(f"❌ Failed to retrieve history: {result['error']}")
                
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Error during lookup: {e}")
            
            # Include traceback for debugging
            if logger:
                logger.error(f"CARFAX test error for {vin}: {traceback.format_exc()}")
        
        finally:
            result['elapsed_seconds'] = round(time.time() - start_time, 2)
            print(f"⏱️  Completed in {result['elapsed_seconds']} seconds")
        
        return result
    
    def _display_summary(self, history_data: Dict[str, Any], flags_analysis: Dict[str, Any]):
        """Display a readable summary of the vehicle history"""
        print("\n📋 Vehicle History Summary")
        print("=" * 30)
        
        # Vehicle info
        vehicle_info = history_data.get('vehicle_info', {})
        if vehicle_info:
            year = vehicle_info.get('year', 'Unknown')
            make = vehicle_info.get('make', 'Unknown')
            model = vehicle_info.get('model', 'Unknown')
            print(f"🚗 Vehicle: {year} {make} {model}")
        
        # Summary stats
        summary = history_data.get('summary', {})
        if summary:
            accident_count = summary.get('accident_count', 0)
            previous_owners = summary.get('previous_owners', 0)
            service_count = summary.get('service_records_count', 0)
            
            print(f"💥 Accidents: {accident_count}")
            print(f"👥 Previous Owners: {previous_owners}")
            print(f"🔧 Service Records: {service_count}")
        
        # Title issues
        title_issues = summary.get('title_issues', [])
        if title_issues:
            print(f"⚠️  Title Issues: {', '.join(title_issues)}")
        
        # Flags analysis
        if flags_analysis:
            risk_level = flags_analysis.get('overall_risk', 'unknown')
            risk_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴', 'unknown': '⚪'}
            print(f"\n{risk_emoji.get(risk_level, '⚪')} Overall Risk: {risk_level.upper()}")
            
            red_flags = flags_analysis.get('red_flags', [])
            if red_flags:
                print("🔴 Red Flags:")
                for flag in red_flags:
                    print(f"  • {flag}")
            
            yellow_flags = flags_analysis.get('yellow_flags', [])
            if yellow_flags:
                print("🟡 Yellow Flags:")
                for flag in yellow_flags:
                    print(f"  • {flag}")
            
            green_flags = flags_analysis.get('green_flags', [])
            if green_flags:
                print("🟢 Green Flags:")
                for flag in green_flags:
                    print(f"  • {flag}")
    
    def run_tests(self, vins: List[str]) -> List[Dict[str, Any]]:
        """Run tests for all provided VINs"""
        if not vins:
            print("❌ No VINs provided for testing")
            return []
        
        print(f"\n🚀 Starting CARFAX tests for {len(vins)} VIN(s)")
        print("=" * 50)
        
        total_start_time = time.time()
        
        for i, vin in enumerate(vins, 1):
            print(f"\n[{i}/{len(vins)}] Processing VIN: {vin}")
            result = self.test_single_vin(vin)
            self.results.append(result)
            
            # Add delay between requests to be respectful
            if i < len(vins):
                print("⏳ Waiting before next request...")
                time.sleep(3)
        
        total_elapsed = round(time.time() - total_start_time, 2)
        
        # Display overall summary
        self._display_overall_summary(total_elapsed)
        
        return self.results
    
    def _display_overall_summary(self, total_elapsed: float):
        """Display overall test summary"""
        print(f"\n📊 Test Summary")
        print("=" * 20)
        
        successful = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - successful
        
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"⏱️  Total Time: {total_elapsed} seconds")
        
        if self.results:
            avg_time = sum(r['elapsed_seconds'] for r in self.results) / len(self.results)
            print(f"📈 Average Time per VIN: {avg_time:.2f} seconds")
    
    def save_results(self, output_file: str = None) -> str:
        """Save test results to JSON file"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"carfax_test_results_{timestamp}.json"
        
        output_path = Path(output_file)
        
        # Prepare results for JSON serialization
        json_results = {
            'test_metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_vins_tested': len(self.results),
                'successful_tests': sum(1 for r in self.results if r['success']),
                'failed_tests': sum(1 for r in self.results if not r['success']),
                'script_version': '1.0'
            },
            'results': self.results
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, indent=2, sort_keys=True, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {output_path.absolute()}")
            return str(output_path.absolute())
            
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
            return ""
    
    def cleanup(self):
        """Clean up resources"""
        if self.integrator:
            try:
                self.integrator.close()
            except Exception as e:
                print(f"⚠️  Warning during cleanup: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Test CARFAX dealer portal integration with specific VINs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--vins',
        nargs='+',
        help='VIN numbers to test (space-separated)'
    )
    
    parser.add_argument(
        '--prompt-credentials',
        action='store_true',
        help='Prompt for credentials even if environment variables are set'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout in seconds for each VIN lookup (default: 30)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file for results (default: auto-generated with timestamp)'
    )
    
    args = parser.parse_args()
    
    print("🚗 CARFAX Integration Test Script")
    print("=" * 40)
    
    tester = CarfaxTester(timeout=args.timeout)
    
    try:
        # Get credentials
        tester.get_credentials(args.prompt_credentials)
        
        # Get VINs to test
        if args.vins:
            vins = []
            for vin in args.vins:
                vin = vin.upper().strip()
                if tester.validate_vin(vin):
                    vins.append(vin)
                else:
                    print(f"❌ Invalid VIN format: {vin}")
        else:
            vins = tester.get_vins_interactive()
        
        if not vins:
            print("❌ No valid VINs to test")
            return 1
        
        # Run tests
        results = tester.run_tests(vins)
        
        # Save results
        output_file = tester.save_results(args.output)
        
        # Final status
        successful = sum(1 for r in results if r['success'])
        if successful == len(results):
            print(f"\n🎉 All {len(results)} tests completed successfully!")
            return 0
        elif successful > 0:
            print(f"\n⚠️  {successful}/{len(results)} tests completed successfully")
            return 1
        else:
            print(f"\n❌ All {len(results)} tests failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if logger:
            logger.error(f"Test script error: {traceback.format_exc()}")
        return 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
