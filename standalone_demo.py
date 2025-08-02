#!/usr/bin/env python3
"""
Standalone CarMax AI Agent Demo
Demonstrates core functionality without PyTorch dependencies
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
import sys
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add current directory to path
sys.path.insert(0, '.')

@dataclass
class VehicleData:
    """Data structure for vehicle information"""
    url: str
    vin: str = ""
    year: int = 0
    make: str = ""
    model: str = ""
    trim: str = ""
    mileage: int = 0
    price: float = 0.0
    location: str = ""
    condition_grade: str = ""
    images: List[str] = None
    autocheck_url: str = ""
    raw_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.raw_data is None:
            self.raw_data = {}

def test_basic_functionality():
    """Test basic data structures and functionality"""
    print("=" * 60)
    print("CARMAX AI AGENT - STANDALONE DEMO")
    print("=" * 60)
    
    print("\n1. Testing Core Data Structures...")
    
    # Test VehicleData creation
    try:
        vehicle = VehicleData(
            url="https://carmaxauctions.com/demo/12345",
            vin="1HGBH41JXMN109186",
            year=2021,
            make="Honda",
            model="Civic",
            mileage=45000,
            price=18500.0,
            location="Atlanta, GA"
        )
        
        print(f"✓ VehicleData created successfully")
        print(f"  - Vehicle: {vehicle.year} {vehicle.make} {vehicle.model}")
        print(f"  - VIN: {vehicle.vin}")
        print(f"  - Price: ${vehicle.price:,.2f}")
        print(f"  - Mileage: {vehicle.mileage:,} miles")
        
        return vehicle
        
    except Exception as e:
        print(f"✗ VehicleData creation failed: {e}")
        return None

def create_mock_autocheck_report(output_dir: Path) -> str:
    """Create a mock AutoCheck report"""
    report_content = """
AutoCheck Vehicle History Report

Vehicle Information:
VIN: 1HGBH41JXMN109186
Year: 2021
Make: HONDA
Model: CIVIC
Mileage: 45,000

AutoCheck Score: 85 out of 100

History Records:
01/15/2021 - Vehicle manufactured
02/20/2021 - First registration in Georgia
03/10/2021 - Sold at auction
06/15/2022 - Registration renewal
12/01/2022 - Inspection passed
05/20/2023 - Service record - oil change
11/10/2023 - Registration renewal
01/05/2024 - Minor accident reported - rear bumper
03/15/2024 - Repair completed
07/20/2024 - Inspection passed

Summary:
- 1 accident reported
- Regular maintenance records
- Clean title
- No flood, fire, or lemon history
"""
    
    report_path = output_dir / "autocheck_report.txt"
    with open(report_path, 'w') as f:
        f.write(report_content)
    
    return str(report_path)

async def test_autocheck_analyzer():
    """Test AutoCheck analyzer functionality"""
    print("\n2. Testing AutoCheck Analyzer...")
    
    try:
        # Import only the AutoCheck analyzer
        from agents.autocheck import AutoCheckAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock report
            mock_report = create_mock_autocheck_report(temp_path)
            print(f"✓ Created mock AutoCheck report")
            
            # Initialize analyzer
            analyzer = AutoCheckAnalyzer()
            print(f"✓ AutoCheck analyzer initialized")
            
            # Analyze report
            results = await analyzer.analyze_report(mock_report)
            
            if "error" not in results:
                analysis = results.get('analysis', {})
                print(f"✓ AutoCheck analysis completed")
                print(f"  - Risk score: {analysis.get('risk_score', 'unknown')}")
                print(f"  - Total records: {analysis.get('total_records', 0)}")
                print(f"  - Red flags: {len(analysis.get('red_flags', []))}")
                
                # Show risk factors
                risk_factors = analysis.get('risk_factors', [])
                if risk_factors:
                    print(f"  - Risk factors:")
                    for factor in risk_factors[:3]:
                        print(f"    • {factor.get('type', 'unknown')}: {factor.get('event', 'N/A')}")
                
                # Show recommendations
                recommendations = analysis.get('recommendations', [])
                if recommendations:
                    print(f"  - Recommendations:")
                    for rec in recommendations[:2]:
                        print(f"    • {rec}")
                
                return results
            else:
                print(f"✗ AutoCheck analysis failed: {results['error']}")
                return None
                
    except Exception as e:
        print(f"✗ AutoCheck analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_ollama_connection():
    """Test Ollama connection"""
    print("\n3. Testing Ollama Connection...")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✓ Ollama server connected")
            print(f"  - Available models: {len(models)}")
            for model in models:
                print(f"    - {model['name']}")
            
            # Test simple generation
            test_payload = {
                "model": "llama3.2:1b",
                "prompt": "Describe a 2021 Honda Civic in one sentence.",
                "stream": False,
                "options": {"num_predict": 30}
            }
            
            gen_response = requests.post(
                "http://localhost:11434/api/generate",
                json=test_payload,
                timeout=30
            )
            
            if gen_response.status_code == 200:
                result = gen_response.json()
                response_text = result.get("response", "").strip()
                print(f"✓ Text generation test successful")
                print(f"  - Response: '{response_text}'")
                return True
            else:
                print(f"✗ Text generation failed: HTTP {gen_response.status_code}")
                return False
        else:
            print(f"✗ Ollama server not responding: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Ollama connection test failed: {e}")
        return False

async def test_ai_notes_generator():
    """Test AI Notes generator functionality"""
    print("\n4. Testing AI Notes Generator...")
    
    try:
        # Import only the notes generator
        from agents.note_gen import AINotesGenerator
        
        # Create mock vehicle data
        class MockVehicleData:
            def __init__(self):
                self.vin = "1HGBH41JXMN109186"
                self.year = 2021
                self.make = "Honda"
                self.model = "Civic"
                self.trim = "LX"
                self.mileage = 45000
                self.price = 18500.0
                self.location = "Atlanta, GA"
                self.condition_grade = "Good"
        
        vehicle_data = MockVehicleData()
        print(f"✓ Created mock vehicle data")
        
        # Mock analysis results (no vision analysis to avoid PyTorch)
        vision_analysis = {
            "note": "Vision analysis not available - PyTorch dependency issue",
            "exterior_analysis": {"overall_condition": "unknown"},
            "damage_assessment": {"damage_severity": 0},
            "condition_summary": {"overall_condition": "unknown"}
        }
        
        autocheck_analysis = {
            "analysis": {
                "risk_score": 25,
                "red_flags": ["Minor accident reported"],
                "total_records": 10,
                "summary": {"recommendation": "CONSIDER"}
            }
        }
        
        # Initialize generator
        generator = AINotesGenerator(model_name="llama3.2:1b")
        print(f"✓ AI Notes generator initialized")
        
        # Generate notes
        notes = await generator.generate_notes(vehicle_data, vision_analysis, autocheck_analysis)
        
        if "error" not in notes:
            print(f"✓ AI notes generation completed")
            
            # Show generated content
            if notes.get("vehicle_summary"):
                summary = notes["vehicle_summary"][:100] + "..." if len(notes["vehicle_summary"]) > 100 else notes["vehicle_summary"]
                print(f"  - Vehicle summary: {summary}")
            
            if notes.get("key_findings"):
                print(f"  - Key findings ({len(notes['key_findings'])} items):")
                for i, finding in enumerate(notes["key_findings"][:3], 1):
                    print(f"    {i}. {finding}")
            
            if notes.get("recommendations"):
                rec = notes["recommendations"]
                if isinstance(rec, dict):
                    if rec.get("overall"):
                        print(f"  - Overall recommendation: {rec['overall']}")
                    if rec.get("reasoning"):
                        reasoning = rec["reasoning"][:80] + "..." if len(rec["reasoning"]) > 80 else rec["reasoning"]
                        print(f"  - Reasoning: {reasoning}")
            
            return notes
        else:
            print(f"✗ AI notes generation failed: {notes['error']}")
            return None
            
    except Exception as e:
        print(f"✗ AI Notes generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_complete_workflow():
    """Test a complete analysis workflow"""
    print("\n5. Testing Complete Analysis Workflow...")
    
    try:
        # Create vehicle data
        vehicle_data = VehicleData(
            url="https://carmaxauctions.com/demo/12345",
            vin="1HGBH41JXMN109186",
            year=2021,
            make="Honda",
            model="Civic",
            trim="LX",
            mileage=45000,
            price=18500.0,
            location="Atlanta, GA",
            condition_grade="Good"
        )
        
        print(f"✓ Vehicle data prepared: {vehicle_data.year} {vehicle_data.make} {vehicle_data.model}")
        
        # Run AutoCheck analysis
        autocheck_results = await test_autocheck_analyzer()
        
        if not autocheck_results:
            print(f"✗ Workflow failed at AutoCheck analysis")
            return False
        
        # Run AI notes generation
        ai_notes = await test_ai_notes_generator()
        
        if not ai_notes:
            print(f"✗ Workflow failed at AI notes generation")
            return False
        
        # Calculate condition score (simplified)
        print(f"\n   Calculating condition score...")
        
        base_score = 85.0
        condition_score = base_score
        red_flags = []
        
        # Apply AutoCheck penalties
        analysis = autocheck_results.get("analysis", {})
        risk_score = analysis.get("risk_score", 0)
        autocheck_red_flags = analysis.get("red_flags", [])
        
        condition_score -= risk_score * 0.5  # Reduce by half the risk score
        red_flags.extend(autocheck_red_flags)
        
        # Age and mileage considerations
        current_year = datetime.now().year
        age = current_year - vehicle_data.year
        expected_mileage = age * 12000
        
        if vehicle_data.mileage > expected_mileage * 1.3:
            condition_score -= 10
            red_flags.append("High mileage for vehicle age")
        
        # Generate final recommendation
        if condition_score >= 80 and len(red_flags) <= 1:
            recommendation = "RECOMMENDED - Good condition vehicle"
        elif condition_score >= 65:
            recommendation = "CONSIDER - Some issues noted"
        elif condition_score >= 50:
            recommendation = "CAUTION - Multiple concerns"
        else:
            recommendation = "AVOID - Significant issues"
        
        # Display final results
        print(f"\n   COMPLETE ANALYSIS RESULTS:")
        print(f"   " + "=" * 40)
        print(f"   Vehicle: {vehicle_data.year} {vehicle_data.make} {vehicle_data.model}")
        print(f"   VIN: {vehicle_data.vin}")
        print(f"   Price: ${vehicle_data.price:,.2f}")
        print(f"   Mileage: {vehicle_data.mileage:,} miles")
        print(f"   Age: {age} years")
        print(f"   Condition Score: {condition_score:.1f}/100")
        print(f"   Recommendation: {recommendation}")
        
        if red_flags:
            print(f"   Red Flags ({len(red_flags)}):")
            for flag in red_flags:
                print(f"     ⚠️  {flag}")
        else:
            print(f"   ✅ No red flags identified")
        
        # Show AI insights
        if ai_notes and ai_notes.get("key_findings"):
            print(f"   Key AI Insights:")
            for i, finding in enumerate(ai_notes["key_findings"][:3], 1):
                print(f"     {i}. {finding}")
        
        # Create summary report
        report = {
            "vehicle": asdict(vehicle_data),
            "autocheck_analysis": autocheck_results,
            "ai_notes": ai_notes,
            "condition_score": condition_score,
            "recommendation": recommendation,
            "red_flags": red_flags,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save report
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(report, f, indent=2, default=str)
            report_path = f.name
        
        print(f"   📄 Analysis report saved to: {report_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ Complete workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def display_system_capabilities():
    """Display system capabilities and status"""
    print(f"\n" + "=" * 60)
    print("SYSTEM CAPABILITIES & STATUS")
    print("=" * 60)
    
    # Check core dependencies
    dependencies = [
        ("requests", "Web scraping and HTTP requests"),
        ("beautifulsoup4", "HTML parsing"),
        ("pdfplumber", "PDF document parsing"),
        ("PIL", "Image processing"),
        ("ollama", "Local LLM integration")
    ]
    
    print(f"\nCore Dependencies:")
    for dep, desc in dependencies:
        try:
            __import__(dep)
            print(f"  ✓ {dep:<15} - {desc}")
        except ImportError:
            print(f"  ✗ {dep:<15} - {desc} (Not available)")
    
    # PyTorch status
    print(f"\nAI Model Dependencies:")
    try:
        import torch
        print(f"  ✓ PyTorch         - Deep learning framework")
        print(f"  ✓ Vision Models   - BLIP/LLaVA for image analysis")
    except Exception as e:
        print(f"  ⚠️  PyTorch         - Deep learning (Issue detected)")
        print(f"  ⚠️  Vision Models   - Using fallback methods")
    
    print(f"\nImplemented Features:")
    print(f"  ✅ Vehicle data structures and management")
    print(f"  ✅ AutoCheck report parsing (PDF/HTML)")
    print(f"  ✅ Local LLM integration via Ollama")
    print(f"  ✅ AI-powered vehicle analysis and notes")
    print(f"  ✅ Risk assessment and scoring")
    print(f"  ✅ Red flag detection")
    print(f"  ✅ Comprehensive reporting (JSON)")
    print(f"  ✅ Batch processing framework")
    print(f"  ⚠️  Vision analysis (fallback mode)")
    print(f"  ⚠️  Web scraping (framework ready)")
    
    print(f"\nReady for Production:")
    print(f"  🔧 Customize scraping for actual CarMax URLs")
    print(f"  🔐 Add authentication for CarMax auctions")
    print(f"  🚀 Scale up for high-volume processing")
    print(f"  📊 Integrate with existing auction systems")

async def main():
    """Main demo function"""
    print("🚗 CarMax AI Agent - Standalone Demo")
    print("Demonstrating core functionality without PyTorch dependencies")
    
    # Test basic functionality
    vehicle_data = test_basic_functionality()
    if not vehicle_data:
        print("\n❌ Basic functionality test failed")
        return
    
    # Test Ollama connection
    ollama_ok = test_ollama_connection()
    
    # Test AutoCheck analyzer
    autocheck_results = await test_autocheck_analyzer()
    
    # Test AI notes generator (if Ollama is available)
    if ollama_ok:
        ai_notes = await test_ai_notes_generator()
    else:
        print("\n⚠️  Skipping AI notes test (Ollama not available)")
        ai_notes = None
    
    # Test complete workflow
    if ollama_ok and autocheck_results:
        workflow_ok = await test_complete_workflow()
    else:
        print("\n⚠️  Skipping complete workflow test")
        workflow_ok = False
    
    # Display system capabilities
    display_system_capabilities()
    
    # Final summary
    print(f"\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    
    print(f"✅ Core Data Structures: Working")
    print(f"{'✅' if autocheck_results else '❌'} AutoCheck Analysis: {'Working' if autocheck_results else 'Failed'}")
    print(f"{'✅' if ollama_ok else '⚠️ '} Ollama Integration: {'Connected' if ollama_ok else 'Not available'}")
    print(f"{'✅' if ai_notes else '⚠️ '} AI Notes Generation: {'Working' if ai_notes else 'Limited'}")
    print(f"{'✅' if workflow_ok else '⚠️ '} Complete Workflow: {'Successful' if workflow_ok else 'Partial'}")
    
    if workflow_ok:
        print(f"\n🎉 CarMax AI Agent core functionality is working!")
        print(f"   Ready for production deployment with minor fixes")
    elif autocheck_results and ollama_ok:
        print(f"\n🚀 CarMax AI Agent is mostly functional!")
        print(f"   Core analysis pipeline working correctly")
    else:
        print(f"\n⚠️  CarMax AI Agent has limited functionality")
        print(f"   Check Ollama installation and dependencies")
    
    print(f"\n📋 Next Steps:")
    print(f"   1. Fix PyTorch installation for full vision analysis")
    print(f"   2. Implement actual CarMax website scraping")
    print(f"   3. Add authentication and session management")
    print(f"   4. Deploy for production use")
    print(f"   5. Scale up for batch processing")
    
    print(f"\n📖 Documentation: See docs/SETUP.md for detailed setup")
    print(f"🔧 Customization: Modify agents/*.py for specific needs")

if __name__ == "__main__":
    asyncio.run(main())
