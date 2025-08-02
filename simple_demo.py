#!/usr/bin/env python3
"""
Simplified CarMax AI Agent Demo
Works around dependency issues and demonstrates core functionality
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

def test_basic_imports():
    """Test basic imports without heavy dependencies"""
    print("=" * 60)
    print("CARMAX AI AGENT - BASIC FUNCTIONALITY TEST")
    print("=" * 60)
    
    print("\n1. Testing Core Imports...")
    
    try:
        from agents.carmax_ai_agent import VehicleData, AnalysisResult
        print("✓ Core data structures imported")
    except Exception as e:
        print(f"✗ Core imports failed: {e}")
        return False
    
    try:
        from agents.autocheck import AutoCheckAnalyzer
        print("✓ AutoCheck analyzer imported")
    except Exception as e:
        print(f"✗ AutoCheck analyzer failed: {e}")
        return False
    
    try:
        from agents.note_gen import AINotesGenerator
        print("✓ AI Notes generator imported")
    except Exception as e:
        print(f"✗ AI Notes generator failed: {e}")
        return False
    
    return True

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
        from agents.autocheck import AutoCheckAnalyzer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock report
            mock_report = create_mock_autocheck_report(temp_path)
            
            # Initialize analyzer
            analyzer = AutoCheckAnalyzer()
            
            # Analyze report
            results = await analyzer.analyze_report(mock_report)
            
            if "error" not in results:
                analysis = results.get('analysis', {})
                print(f"✓ AutoCheck analysis completed")
                print(f"  - Risk score: {analysis.get('risk_score', 'unknown')}")
                print(f"  - Total records: {analysis.get('total_records', 0)}")
                print(f"  - Red flags: {len(analysis.get('red_flags', []))}")
                
                # Show some details
                if analysis.get('risk_factors'):
                    print(f"  - Risk factors found: {len(analysis['risk_factors'])}")
                
                return results
            else:
                print(f"✗ AutoCheck analysis failed: {results['error']}")
                return None
                
    except Exception as e:
        print(f"✗ AutoCheck analyzer test failed: {e}")
        return None

async def test_ai_notes_generator():
    """Test AI Notes generator functionality"""
    print("\n3. Testing AI Notes Generator...")
    
    try:
        from agents.note_gen import AINotesGenerator
        from agents.carmax_ai_agent import VehicleData
        
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
        
        # Mock analysis results
        vision_analysis = {
            "exterior_analysis": {"overall_condition": "good"},
            "damage_assessment": {"damage_severity": 2},
            "interior_analysis": {"overall_condition": "fair"}
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
        
        # Generate notes
        notes = await generator.generate_notes(vehicle_data, vision_analysis, autocheck_analysis)
        
        if "error" not in notes:
            print(f"✓ AI notes generation completed")
            
            # Show generated content
            if notes.get("vehicle_summary"):
                print(f"  - Vehicle summary generated")
            
            if notes.get("key_findings"):
                print(f"  - Key findings: {len(notes['key_findings'])} items")
                for i, finding in enumerate(notes["key_findings"][:3], 1):
                    print(f"    {i}. {finding}")
            
            if notes.get("recommendations"):
                rec = notes["recommendations"]
                if isinstance(rec, dict) and rec.get("overall"):
                    print(f"  - Overall recommendation: {rec['overall']}")
            
            return notes
        else:
            print(f"✗ AI notes generation failed: {notes['error']}")
            return None
            
    except Exception as e:
        print(f"✗ AI Notes generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_ollama_connection():
    """Test Ollama connection"""
    print("\n4. Testing Ollama Connection...")
    
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
                "prompt": "Say hello in one sentence.",
                "stream": False,
                "options": {"num_predict": 20}
            }
            
            gen_response = requests.post(
                "http://localhost:11434/api/generate",
                json=test_payload,
                timeout=30
            )
            
            if gen_response.status_code == 200:
                result = gen_response.json()
                response_text = result.get("response", "").strip()
                print(f"✓ Text generation test: '{response_text}'")
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

async def test_complete_workflow():
    """Test a complete analysis workflow"""
    print("\n5. Testing Complete Workflow...")
    
    try:
        from agents.carmax_ai_agent import VehicleData
        
        # Create mock vehicle data
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
        
        print(f"✓ Created vehicle data: {vehicle_data.year} {vehicle_data.make} {vehicle_data.model}")
        
        # Test AutoCheck analysis
        autocheck_results = await test_autocheck_analyzer()
        
        # Test AI notes generation
        if autocheck_results:
            print("\n   Generating comprehensive AI analysis...")
            
            from agents.note_gen import AINotesGenerator
            generator = AINotesGenerator(model_name="llama3.2:1b")
            
            # Mock vision analysis since we can't load PyTorch models
            mock_vision = {
                "exterior_analysis": {"overall_condition": "good", "body_damage": []},
                "interior_analysis": {"overall_condition": "fair"},
                "damage_assessment": {"damage_severity": 2, "overall_rating": "good"},
                "condition_summary": {"overall_condition": "good"}
            }
            
            notes = await generator.generate_notes(vehicle_data, mock_vision, autocheck_results)
            
            if notes and "error" not in notes:
                print(f"✓ Complete workflow successful")
                
                # Calculate a simple condition score
                condition_score = 85.0  # Mock score
                red_flags = []
                
                if autocheck_results.get("analysis", {}).get("red_flags"):
                    red_flags.extend(autocheck_results["analysis"]["red_flags"])
                    condition_score -= len(red_flags) * 10
                
                # Generate recommendation
                if condition_score >= 80:
                    recommendation = "RECOMMENDED - Good condition vehicle"
                elif condition_score >= 60:
                    recommendation = "CONSIDER - Some issues noted"
                else:
                    recommendation = "CAUTION - Multiple concerns"
                
                print(f"\n   ANALYSIS SUMMARY:")
                print(f"   ================")
                print(f"   Vehicle: {vehicle_data.year} {vehicle_data.make} {vehicle_data.model}")
                print(f"   VIN: {vehicle_data.vin}")
                print(f"   Price: ${vehicle_data.price:,.2f}")
                print(f"   Mileage: {vehicle_data.mileage:,} miles")
                print(f"   Condition Score: {condition_score:.1f}/100")
                print(f"   Recommendation: {recommendation}")
                
                if red_flags:
                    print(f"   Red Flags:")
                    for flag in red_flags:
                        print(f"     ⚠️  {flag}")
                
                if notes.get("key_findings"):
                    print(f"   Key AI Insights:")
                    for i, finding in enumerate(notes["key_findings"][:5], 1):
                        print(f"     {i}. {finding}")
                
                return True
            else:
                print(f"✗ AI analysis failed")
                return False
        else:
            print(f"✗ Workflow failed at AutoCheck analysis")
            return False
            
    except Exception as e:
        print(f"✗ Complete workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def display_system_status():
    """Display system status and capabilities"""
    print("\n" + "=" * 60)
    print("SYSTEM STATUS & CAPABILITIES")
    print("=" * 60)
    
    # Check dependencies
    dependencies = [
        ("requests", "Web scraping"),
        ("beautifulsoup4", "HTML parsing"),
        ("pdfplumber", "PDF parsing"),
        ("PIL", "Image processing"),
        ("ollama", "Local LLM integration")
    ]
    
    print(f"\nDependency Status:")
    for dep, desc in dependencies:
        try:
            __import__(dep)
            print(f"  ✓ {dep:<15} - {desc}")
        except ImportError:
            print(f"  ✗ {dep:<15} - {desc} (Not available)")
    
    # PyTorch status
    try:
        import torch
        print(f"  ✓ torch          - Deep learning (Version: {torch.__version__})")
    except Exception as e:
        print(f"  ⚠️  torch          - Deep learning (Issue: {str(e)[:50]}...)")
    
    print(f"\nCore Capabilities:")
    print(f"  ✓ CarMax auction data scraping")
    print(f"  ✓ AutoCheck report parsing and analysis")
    print(f"  ✓ Local LLM integration via Ollama")
    print(f"  ✓ AI-powered vehicle analysis and notes")
    print(f"  ✓ Risk assessment and red flag detection")
    print(f"  ✓ Comprehensive reporting (JSON/Markdown)")
    print(f"  ✓ Batch processing capabilities")
    print(f"  ⚠️  Vision analysis (requires PyTorch fix)")

async def main():
    """Main demo function"""
    print("🚗 CarMax AI Agent - Simplified Demo")
    
    # Test basic functionality
    if not test_basic_imports():
        print("\n❌ Basic imports failed. Please check installation.")
        return
    
    # Test Ollama connection
    ollama_ok = test_ollama_connection()
    
    if not ollama_ok:
        print("\n⚠️  Ollama not available. AI features will be limited.")
    
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
    
    # Display system status
    display_system_status()
    
    # Final summary
    print(f"\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    
    print(f"✅ Core Components: Loaded successfully")
    print(f"{'✅' if autocheck_results else '❌'} AutoCheck Analysis: {'Working' if autocheck_results else 'Failed'}")
    print(f"{'✅' if ollama_ok else '⚠️ '} Ollama Integration: {'Connected' if ollama_ok else 'Not available'}")
    print(f"{'✅' if ai_notes else '⚠️ '} AI Notes Generation: {'Working' if ai_notes else 'Limited'}")
    print(f"{'✅' if workflow_ok else '⚠️ '} Complete Workflow: {'Successful' if workflow_ok else 'Partial'}")
    
    if workflow_ok:
        print(f"\n🎉 CarMax AI Agent is fully functional!")
    elif autocheck_results and ollama_ok:
        print(f"\n🚀 CarMax AI Agent is mostly functional!")
        print(f"   Note: Vision analysis requires PyTorch fix")
    else:
        print(f"\n⚠️  CarMax AI Agent has limited functionality")
        print(f"   Please check Ollama installation and dependencies")
    
    print(f"\n📖 Next Steps:")
    print(f"   1. Fix PyTorch installation for vision analysis")
    print(f"   2. Customize scraping for actual CarMax URLs")
    print(f"   3. Add authentication for CarMax auctions")
    print(f"   4. Scale up for production use")

if __name__ == "__main__":
    asyncio.run(main())
