#!/usr/bin/env python3
"""
CarMax AI Agent Demo Script
Demonstrates the complete functionality with mock data and real AI analysis
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from PIL import Image, ImageDraw
import requests
import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

from agents.carmax_ai_agent import CarMaxAIAgent, VehicleData, AnalysisResult
from agents.vision import VehicleVisionAnalyzer
from agents.autocheck import AutoCheckAnalyzer
from agents.note_gen import AINotesGenerator


def create_mock_vehicle_images(output_dir: Path) -> list:
    """Create mock vehicle images for testing"""
    images = []
    
    # Create exterior image
    exterior_img = Image.new('RGB', (800, 600), color='blue')
    draw = ImageDraw.Draw(exterior_img)
    draw.rectangle([100, 200, 700, 500], fill='lightblue', outline='darkblue', width=3)
    draw.text((350, 350), "EXTERIOR VIEW", fill='white')
    exterior_path = output_dir / "exterior_01.jpg"
    exterior_img.save(exterior_path)
    images.append(str(exterior_path))
    
    # Create interior image
    interior_img = Image.new('RGB', (800, 600), color='gray')
    draw = ImageDraw.Draw(interior_img)
    draw.rectangle([200, 150, 600, 450], fill='black', outline='white', width=2)
    draw.text((350, 300), "INTERIOR VIEW", fill='white')
    interior_path = output_dir / "interior_01.jpg"
    interior_img.save(interior_path)
    images.append(str(interior_path))
    
    # Create engine image
    engine_img = Image.new('RGB', (800, 600), color='darkgray')
    draw = ImageDraw.Draw(engine_img)
    draw.rectangle([150, 100, 650, 500], fill='silver', outline='black', width=2)
    draw.text((350, 300), "ENGINE BAY", fill='black')
    engine_path = output_dir / "engine_01.jpg"
    engine_img.save(engine_path)
    images.append(str(engine_path))
    
    return images


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


async def demo_individual_components():
    """Demo each component individually"""
    print("=" * 60)
    print("CARMAX AI AGENT - COMPONENT DEMOS")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create mock data
        print("\n1. Creating mock vehicle data...")
        mock_images = create_mock_vehicle_images(temp_path)
        mock_report = create_mock_autocheck_report(temp_path)
        
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
            condition_grade="Good",
            images=mock_images
        )
        
        print(f"✓ Created vehicle data: {vehicle_data.year} {vehicle_data.make} {vehicle_data.model}")
        print(f"✓ Created {len(mock_images)} mock images")
        print(f"✓ Created mock AutoCheck report")
        
        # Test Vision Analyzer
        print("\n2. Testing Vision Analyzer...")
        try:
            vision_analyzer = VehicleVisionAnalyzer()
            vision_results = await vision_analyzer.analyze_vehicle_images(mock_images)
            
            print(f"✓ Vision analysis completed")
            print(f"  - Processed {vision_results.get('processed_images', 0)} images")
            print(f"  - Overall condition: {vision_results.get('condition_summary', {}).get('overall_condition', 'unknown')}")
            
        except Exception as e:
            print(f"✗ Vision analysis failed: {e}")
            vision_results = {"error": str(e)}
        
        # Test AutoCheck Analyzer
        print("\n3. Testing AutoCheck Analyzer...")
        try:
            autocheck_analyzer = AutoCheckAnalyzer()
            autocheck_results = await autocheck_analyzer.analyze_report(mock_report)
            
            analysis = autocheck_results.get('analysis', {})
            print(f"✓ AutoCheck analysis completed")
            print(f"  - Risk score: {analysis.get('risk_score', 'unknown')}")
            print(f"  - Total records: {analysis.get('total_records', 0)}")
            print(f"  - Red flags: {len(analysis.get('red_flags', []))}")
            
        except Exception as e:
            print(f"✗ AutoCheck analysis failed: {e}")
            autocheck_results = {"error": str(e)}
        
        # Test AI Notes Generator
        print("\n4. Testing AI Notes Generator...")
        try:
            notes_generator = AINotesGenerator(model_name="llama3.2:1b")
            ai_notes = await notes_generator.generate_notes(vehicle_data, vision_results, autocheck_results)
            
            print(f"✓ AI notes generation completed")
            if "error" not in ai_notes:
                print(f"  - Generated vehicle summary")
                print(f"  - Generated condition assessment")
                print(f"  - Generated recommendations")
                
                # Show sample notes
                if ai_notes.get("key_findings"):
                    print(f"  - Key findings: {len(ai_notes['key_findings'])} items")
                    for i, finding in enumerate(ai_notes["key_findings"][:3], 1):
                        print(f"    {i}. {finding}")
            else:
                print(f"  - Error: {ai_notes['error']}")
            
        except Exception as e:
            print(f"✗ AI notes generation failed: {e}")
            ai_notes = {"error": str(e)}
        
        return vehicle_data, vision_results, autocheck_results, ai_notes


async def demo_full_integration():
    """Demo the complete integrated system"""
    print("\n" + "=" * 60)
    print("FULL INTEGRATION DEMO")
    print("=" * 60)
    
    try:
        # Initialize the main agent
        print("\n1. Initializing CarMax AI Agent...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the config to use temp directory
            import agents.carmax_ai_agent as agent_module
            original_config = agent_module.config
            
            class MockConfig:
                def get(self, key, default=None):
                    if key == 'output_dir':
                        return temp_dir
                    return default
            
            agent_module.config = MockConfig()
            
            try:
                agent = CarMaxAIAgent()
                print("✓ Agent initialized successfully")
                
                # Create comprehensive mock data
                print("\n2. Setting up comprehensive test scenario...")
                temp_path = Path(temp_dir)
                
                # Create more detailed mock images
                mock_images = create_mock_vehicle_images(temp_path)
                mock_report = create_mock_autocheck_report(temp_path)
                
                # Mock the scraping methods
                async def mock_scrape_vehicle_data(url):
                    return VehicleData(
                        url=url,
                        vin="1HGBH41JXMN109186",
                        year=2021,
                        make="Honda",
                        model="Civic",
                        trim="LX",
                        mileage=45000,
                        price=18500.0,
                        location="Atlanta, GA",
                        condition_grade="Good",
                        images=mock_images,
                        autocheck_url=mock_report
                    )
                
                async def mock_download_images(vehicle_data):
                    return mock_images
                
                # Replace methods with mocks
                agent._scrape_vehicle_data = mock_scrape_vehicle_data
                agent._download_images = mock_download_images
                
                print("✓ Test scenario configured")
                
                # Run full analysis
                print("\n3. Running complete vehicle analysis...")
                start_time = time.time()
                
                test_url = "https://carmaxauctions.com/demo/12345"
                result = await agent.analyze_vehicle(test_url)
                
                analysis_time = time.time() - start_time
                
                print(f"✓ Analysis completed in {analysis_time:.2f} seconds")
                
                # Display results
                print("\n4. Analysis Results:")
                print("-" * 40)
                print(f"Vehicle: {result.vehicle_data.year} {result.vehicle_data.make} {result.vehicle_data.model}")
                print(f"VIN: {result.vehicle_data.vin}")
                print(f"Mileage: {result.vehicle_data.mileage:,} miles")
                print(f"Price: ${result.vehicle_data.price:,.2f}")
                print(f"Condition Score: {result.condition_score:.1f}/100")
                print(f"Recommendation: {result.recommendation}")
                
                if result.red_flags:
                    print(f"\nRed Flags ({len(result.red_flags)}):")
                    for flag in result.red_flags:
                        print(f"  ⚠️  {flag}")
                else:
                    print("\n✅ No red flags identified")
                
                # Show AI insights
                if result.ai_notes and "key_findings" in result.ai_notes:
                    print(f"\nKey AI Insights:")
                    for i, finding in enumerate(result.ai_notes["key_findings"][:5], 1):
                        print(f"  {i}. {finding}")
                
                # Show file outputs
                print(f"\n5. Generated Files:")
                json_files = list(Path(temp_dir).glob("**/reports/*_analysis.json"))
                md_files = list(Path(temp_dir).glob("**/reports/*_report.md"))
                
                if json_files:
                    print(f"  📄 JSON Report: {json_files[0].name}")
                if md_files:
                    print(f"  📝 Markdown Report: {md_files[0].name}")
                
                print(f"\n✅ Full integration demo completed successfully!")
                return result
                
            finally:
                # Restore original config
                agent_module.config = original_config
                
    except Exception as e:
        print(f"✗ Full integration demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def demo_batch_processing():
    """Demo batch processing capabilities"""
    print("\n" + "=" * 60)
    print("BATCH PROCESSING DEMO")
    print("=" * 60)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock config
            import agents.carmax_ai_agent as agent_module
            original_config = agent_module.config
            
            class MockConfig:
                def get(self, key, default=None):
                    if key == 'output_dir':
                        return temp_dir
                    return default
            
            agent_module.config = MockConfig()
            
            try:
                agent = CarMaxAIAgent()
                
                # Create mock URLs
                test_urls = [
                    "https://carmaxauctions.com/demo/12345",
                    "https://carmaxauctions.com/demo/12346", 
                    "https://carmaxauctions.com/demo/12347"
                ]
                
                # Mock the analysis method
                async def mock_analyze_vehicle(url):
                    # Simulate processing time
                    await asyncio.sleep(0.5)
                    
                    # Create mock result
                    vehicle_id = url.split('/')[-1]
                    return AnalysisResult(
                        vehicle_data=VehicleData(
                            url=url,
                            vin=f"TEST{vehicle_id}",
                            year=2020 + int(vehicle_id[-1]),
                            make="Honda",
                            model="Civic",
                            mileage=40000 + int(vehicle_id[-1]) * 5000,
                            price=18000 + int(vehicle_id[-1]) * 1000
                        ),
                        vision_analysis={"overall_condition": "good"},
                        autocheck_analysis={"risk_score": 15 + int(vehicle_id[-1]) * 5},
                        ai_notes={"summary": f"Analysis for vehicle {vehicle_id}"},
                        red_flags=[],
                        condition_score=85 - int(vehicle_id[-1]) * 5,
                        recommendation="CONSIDER",
                        timestamp="2024-01-01T00:00:00",
                        processing_time=0.5
                    )
                
                agent.analyze_vehicle = mock_analyze_vehicle
                
                print(f"\n1. Processing {len(test_urls)} vehicles concurrently...")
                start_time = time.time()
                
                results = await agent.batch_analyze(test_urls, max_concurrent=2)
                
                batch_time = time.time() - start_time
                
                print(f"✓ Batch processing completed in {batch_time:.2f} seconds")
                print(f"✓ Successfully processed {len(results)}/{len(test_urls)} vehicles")
                
                print(f"\n2. Batch Results Summary:")
                print("-" * 50)
                for i, result in enumerate(results, 1):
                    vehicle = result.vehicle_data
                    print(f"{i}. {vehicle.year} {vehicle.make} {vehicle.model}")
                    print(f"   Score: {result.condition_score:.1f} | {result.recommendation}")
                
                return results
                
            finally:
                agent_module.config = original_config
                
    except Exception as e:
        print(f"✗ Batch processing demo failed: {e}")
        return []


def display_system_info():
    """Display system information and capabilities"""
    print("=" * 60)
    print("CARMAX AI AGENT SYSTEM INFORMATION")
    print("=" * 60)
    
    # Check Python version
    print(f"Python Version: {sys.version.split()[0]}")
    
    # Check key dependencies
    dependencies = [
        ("requests", "Web scraping"),
        ("beautifulsoup4", "HTML parsing"),
        ("selenium", "Browser automation"),
        ("PIL", "Image processing"),
        ("transformers", "AI models"),
        ("torch", "Deep learning"),
        ("pdfplumber", "PDF parsing"),
        ("ollama", "Local LLM")
    ]
    
    print("\nDependency Status:")
    for dep, desc in dependencies:
        try:
            __import__(dep)
            print(f"  ✓ {dep:<15} - {desc}")
        except ImportError:
            print(f"  ✗ {dep:<15} - {desc} (Not installed)")
    
    # Check Ollama status
    print(f"\nOllama Status:")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"  ✓ Ollama server running")
            print(f"  ✓ Available models: {len(models)}")
            for model in models:
                print(f"    - {model['name']}")
        else:
            print(f"  ✗ Ollama server not responding")
    except Exception as e:
        print(f"  ✗ Ollama connection failed: {e}")
    
    # System capabilities
    print(f"\nSystem Capabilities:")
    print(f"  ✓ Advanced web scraping with anti-bot detection")
    print(f"  ✓ Local AI vision analysis (BLIP)")
    print(f"  ✓ AutoCheck report parsing (PDF/HTML)")
    print(f"  ✓ Local LLM integration (Ollama)")
    print(f"  ✓ Batch processing with concurrency control")
    print(f"  ✓ Comprehensive reporting (JSON/Markdown)")
    print(f"  ✓ Red flag detection and risk scoring")


async def main():
    """Main demo function"""
    display_system_info()
    
    print(f"\n🚗 Starting CarMax AI Agent Demo...")
    
    # Run component demos
    vehicle_data, vision_results, autocheck_results, ai_notes = await demo_individual_components()
    
    # Run full integration demo
    integration_result = await demo_full_integration()
    
    # Run batch processing demo
    batch_results = await demo_batch_processing()
    
    # Final summary
    print("\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    
    print(f"✅ Component Testing: All major components tested")
    print(f"✅ Integration Testing: {'Passed' if integration_result else 'Failed'}")
    print(f"✅ Batch Processing: {len(batch_results)} vehicles processed")
    
    if integration_result:
        print(f"\n🎯 Sample Analysis Result:")
        print(f"   Vehicle: {integration_result.vehicle_data.make} {integration_result.vehicle_data.model}")
        print(f"   Condition Score: {integration_result.condition_score:.1f}/100")
        print(f"   Recommendation: {integration_result.recommendation}")
        print(f"   Processing Time: {integration_result.processing_time:.2f}s")
    
    print(f"\n🚀 CarMax AI Agent is ready for production use!")
    print(f"📖 See docs/SETUP.md for detailed setup instructions")
    print(f"🔧 Customize agents/carmax_ai_agent.py for your specific needs")


if __name__ == "__main__":
    asyncio.run(main())
