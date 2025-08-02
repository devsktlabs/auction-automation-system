
#!/usr/bin/env python3
"""
Test suite for CarMax AI Agent
"""

import asyncio
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the parent directory to the path so we can import the agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.carmax_ai_agent import CarMaxAIAgent, VehicleData, AnalysisResult
from agents.vision import VehicleVisionAnalyzer
from agents.autocheck import AutoCheckAnalyzer
from agents.note_gen import AINotesGenerator


class TestCarMaxAIAgent:
    """Test cases for CarMax AI Agent"""
    
    @pytest.fixture
    def agent(self):
        """Create a test agent instance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock config to use temp directory
            with patch('agents.carmax_ai_agent.config') as mock_config:
                mock_config.get.return_value = temp_dir
                agent = CarMaxAIAgent()
                yield agent
    
    @pytest.fixture
    def sample_vehicle_data(self):
        """Sample vehicle data for testing"""
        return VehicleData(
            url="https://carmaxauctions.com/test/12345",
            vin="1HGBH41JXMN109186",
            year=2021,
            make="Honda",
            model="Civic",
            mileage=45000,
            price=18500.0,
            location="Atlanta, GA",
            images=["https://imgs.search.brave.com/DTKchjptdSVDJ6kBvcwF4lTH2Q_DFdsclE_v9UdzQnw/rs:fit:500:0:1:0/g:ce/aHR0cHM6Ly9zdGF0/aWMuY2FyZ3VydXMu/Y29tL2ltYWdlcy9m/b3JzYWxlLzIwMjUv/MDcvMTYvMDkvMTQv/MjAxNl9ob25kYV9j/aXZpYy1waWMtODYx/NjcwOTg3MjY3Njcz/MDcyNS0xMDI0eDc2/OC5qcGVnP2lvPXRy/dWUmd2lkdGg9NjQw/JmhlaWdodD00ODAm/Zml0PWJvdW5kcyZm/b3JtYXQ9anBnJmF1/dG89d2VicA", "https://imgs.search.brave.com/Pul5GGQuiVGP_a8IdtShiqf_zMRrZRBTAlOm0HM5ijE/rs:fit:500:0:1:0/g:ce/aHR0cHM6Ly9wbGF0/Zm9ybS5jc3RhdGlj/LWltYWdlcy5jb20v/bGFyZ2UvaW4vdjIv/cDJwL2ZjYTRiZGVk/LTIyMjAtNDQzNS1h/MDNjLWQxOGNhNDM1/YzQ2My8yMjdiZTMw/OC04MmM0LTRiZmMt/YTdkNC0xYzgyYzdk/M2M1YWM"]
        )
    
    def test_agent_initialization(self, agent):
        """Test agent initialization"""
        assert agent is not None
        assert agent.vision_analyzer is not None
        assert agent.autocheck_analyzer is not None
        assert agent.notes_generator is not None
        assert agent.output_dir.exists()
        assert agent.images_dir.exists()
        assert agent.reports_dir.exists()
    
    def test_vehicle_data_creation(self):
        """Test VehicleData creation"""
        data = VehicleData(url="https://test.com")
        assert data.url == "https://test.com"
        assert data.images == []
        assert data.raw_data == {}
    
    @pytest.mark.asyncio
    async def test_scrape_vehicle_data_mock(self, agent, sample_vehicle_data):
        """Test vehicle data scraping with mocked responses"""
        test_url = "https://carmaxauctions.com/test/12345"
        
        # Mock the scraping methods
        with patch.object(agent, '_extract_vehicle_info_selenium') as mock_extract:
            with patch.object(agent, '_extract_image_urls_selenium') as mock_images:
                mock_extract.return_value = sample_vehicle_data
                mock_images.return_value = sample_vehicle_data.images
                
                # Mock driver
                agent.driver = Mock()
                agent.driver.get = Mock()
                
                result = await agent._scrape_vehicle_data(test_url)
                
                assert result.url == test_url
                assert len(result.images) == 2
    
    @pytest.mark.asyncio
    async def test_image_download_mock(self, agent, sample_vehicle_data):
        """Test image downloading with mocked responses"""
        # Mock requests response
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = Mock()
        
        with patch.object(agent.session, 'get', return_value=mock_response):
            paths = await agent._download_images(sample_vehicle_data)
            
            assert len(paths) == 2
            for path in paths:
                assert Path(path).exists()
                assert Path(path).suffix == '.jpg'
    
    @pytest.mark.asyncio
    async def test_condition_score_calculation(self, agent, sample_vehicle_data):
        """Test condition score calculation"""
        vision_analysis = {
            "damage_detected": True,
            "damage_severity": 3
        }
        
        autocheck_analysis = {
            "accidents": True,
            "accident_count": 1
        }
        
        score, red_flags = agent._calculate_condition_score(
            sample_vehicle_data, vision_analysis, autocheck_analysis
        )
        
        assert 0 <= score <= 100
        assert isinstance(red_flags, list)
        assert len(red_flags) >= 1  # Should have at least one red flag
    
    def test_recommendation_generation(self, agent):
        """Test recommendation generation"""
        # Test excellent condition
        rec = agent._generate_recommendation(90, [], {})
        assert "RECOMMENDED" in rec
        
        # Test poor condition
        rec = agent._generate_recommendation(30, ["Major damage"], {})
        assert "AVOID" in rec or "CAUTION" in rec
    
    @pytest.mark.asyncio
    async def test_analysis_result_saving(self, agent, sample_vehicle_data):
        """Test saving analysis results"""
        # Create a mock analysis result
        result = AnalysisResult(
            vehicle_data=sample_vehicle_data,
            vision_analysis={"test": "data"},
            autocheck_analysis={"test": "data"},
            ai_notes={"test": "notes"},
            red_flags=["Test flag"],
            condition_score=75.0,
            recommendation="CONSIDER",
            timestamp="2024-01-01T00:00:00",
            processing_time=1.5
        )
        
        await agent._save_analysis_result(result)
        
        # Check if files were created
        json_files = list(agent.reports_dir.glob("*_analysis.json"))
        md_files = list(agent.reports_dir.glob("*_report.md"))
        
        assert len(json_files) >= 1
        assert len(md_files) >= 1
        
        # Verify JSON content
        with open(json_files[0]) as f:
            saved_data = json.load(f)
            assert saved_data["condition_score"] == 75.0
            assert saved_data["recommendation"] == "CONSIDER"


class TestVehicleVisionAnalyzer:
    """Test cases for Vehicle Vision Analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create a test analyzer instance"""
        return VehicleVisionAnalyzer()
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization"""
        assert analyzer is not None
        assert analyzer.device in ["cpu", "cuda", "mps"]
    
    def test_device_setup(self, analyzer):
        """Test device setup"""
        device = analyzer._setup_device("auto")
        assert device in ["cpu", "cuda", "mps"]
        
        device = analyzer._setup_device("cpu")
        assert device == "cpu"
    
    def test_image_categorization(self, analyzer):
        """Test image categorization logic"""
        # Test interior classification
        category = analyzer._classify_image_category("dashboard and steering wheel", "interior_01.jpg")
        assert category == "interior"
        
        # Test engine classification
        category = analyzer._classify_image_category("engine bay view", "engine_01.jpg")
        assert category == "engine"
        
        # Test default to exterior
        category = analyzer._classify_image_category("side view of car", "exterior_01.jpg")
        assert category == "exterior"
    
    @pytest.mark.asyncio
    async def test_analyze_no_images(self, analyzer):
        """Test analysis with no images"""
        result = await analyzer.analyze_vehicle_images([])
        assert "error" in result
        assert "No images provided" in result["error"]


class TestAutoCheckAnalyzer:
    """Test cases for AutoCheck Analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create a test analyzer instance"""
        return AutoCheckAnalyzer()
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization"""
        assert analyzer is not None
        assert analyzer.risk_indicators is not None
        assert len(analyzer.risk_indicators) > 0
    
    def test_vehicle_info_extraction(self, analyzer):
        """Test vehicle information extraction from text"""
        test_text = """
        Vehicle Information
        VIN: 1HGBH41JXMN109186
        Year: 2021
        Make: HONDA
        Model: CIVIC
        """
        
        info = analyzer._extract_vehicle_info_from_text(test_text)
        
        assert info.get("vin") == "1HGBH41JXMN109186"
        assert info.get("year") == 2021
        assert info.get("make") == "Honda"
    
    def test_history_record_detection(self, analyzer):
        """Test history record detection"""
        # Test with date pattern
        assert analyzer._looks_like_history_record("01/15/2023 Registration renewal")
        
        # Test with history keywords
        assert analyzer._looks_like_history_record("Vehicle inspection completed")
        
        # Test negative case
        assert not analyzer._looks_like_history_record("Random text without indicators")
    
    def test_risk_categorization(self, analyzer):
        """Test risk level categorization"""
        assert analyzer._categorize_risk_level(5) == "very_low"
        assert analyzer._categorize_risk_level(15) == "low"
        assert analyzer._categorize_risk_level(35) == "moderate"
        assert analyzer._categorize_risk_level(60) == "high"
        assert analyzer._categorize_risk_level(80) == "very_high"
    
    @pytest.mark.asyncio
    async def test_analyze_nonexistent_report(self, analyzer):
        """Test analysis with nonexistent report"""
        result = await analyzer.analyze_report("/nonexistent/path.pdf")
        assert "error" in result


class TestAINotesGenerator:
    """Test cases for AI Notes Generator"""
    
    @pytest.fixture
    def generator(self):
        """Create a test generator instance"""
        return AINotesGenerator()
    
    def test_generator_initialization(self, generator):
        """Test generator initialization"""
        assert generator is not None
        assert generator.model_name is not None
        assert generator.templates is not None
    
    def test_context_preparation(self, generator):
        """Test context preparation"""
        # Mock vehicle data
        class MockVehicle:
            vin = "TEST123"
            year = 2021
            make = "Honda"
            model = "Civic"
            mileage = 50000
            price = 20000.0
            location = "Test City"
            condition_grade = "Good"
        
        mock_vehicle = MockVehicle()
        mock_vision = {"test": "vision_data"}
        mock_autocheck = {"test": "autocheck_data"}
        
        context = generator._prepare_context(mock_vehicle, mock_vision, mock_autocheck)
        
        assert context["vehicle"]["vin"] == "TEST123"
        assert context["vehicle"]["year"] == 2021
        assert context["vision_analysis"] == mock_vision
        assert context["autocheck_analysis"] == mock_autocheck
    
    def test_vision_analysis_summary(self, generator):
        """Test vision analysis summarization"""
        vision_data = {
            "exterior_analysis": {"overall_condition": "good"},
            "damage_assessment": {"damage_severity": 3},
            "interior_analysis": {"overall_condition": "fair"}
        }
        
        summary = generator._summarize_vision_analysis(vision_data)
        
        assert "good" in summary.lower()
        assert "3" in summary
        assert "fair" in summary.lower()
    
    def test_autocheck_analysis_summary(self, generator):
        """Test AutoCheck analysis summarization"""
        autocheck_data = {
            "analysis": {
                "risk_score": 25,
                "red_flags": ["Accident reported"],
                "total_records": 12,
                "summary": {"recommendation": "CAUTION"}
            }
        }
        
        summary = generator._summarize_autocheck_analysis(autocheck_data)
        
        assert "25" in summary
        assert "1 red flag" in summary or "red flag" in summary
        assert "12" in summary
        assert "CAUTION" in summary


# Integration tests
class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_analysis_pipeline_mock(self):
        """Test the complete analysis pipeline with mocked components"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock config
            with patch('agents.carmax_ai_agent.config') as mock_config:
                mock_config.get.return_value = temp_dir
                
                agent = CarMaxAIAgent()
                
                # Mock all the analysis methods
                with patch.object(agent, '_scrape_vehicle_data') as mock_scrape:
                    with patch.object(agent, '_analyze_vehicle_images') as mock_vision:
                        with patch.object(agent, '_analyze_autocheck_report') as mock_autocheck:
                            with patch.object(agent, '_generate_ai_notes') as mock_notes:
                                
                                # Setup mock returns
                                mock_scrape.return_value = VehicleData(
                                    url="https://test.com",
                                    vin="TEST123",
                                    year=2021,
                                    make="Honda",
                                    model="Civic"
                                )
                                
                                mock_vision.return_value = {"overall_condition": "good"}
                                mock_autocheck.return_value = {"risk_score": 15}
                                mock_notes.return_value = {"summary": "Good vehicle"}
                                
                                # Run analysis
                                result = await agent.analyze_vehicle("https://test.com")
                                
                                # Verify result
                                assert isinstance(result, AnalysisResult)
                                assert result.vehicle_data.vin == "TEST123"
                                assert result.condition_score >= 0
                                assert result.recommendation is not None


# Test runner
if __name__ == "__main__":
    # Run basic tests
    print("Running CarMax AI Agent tests...")
    
    # Test basic functionality without pytest
    async def run_basic_tests():
        print("Testing agent initialization...")
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('agents.carmax_ai_agent.config') as mock_config:
                mock_config.get.return_value = temp_dir
                agent = CarMaxAIAgent()
                print("✓ Agent initialized successfully")
        
        print("Testing vehicle data creation...")
        data = VehicleData(url="https://test.com")
        assert data.url == "https://test.com"
        print("✓ Vehicle data created successfully")
        
        print("Testing vision analyzer...")
        analyzer = VehicleVisionAnalyzer()
        assert analyzer is not None
        print("✓ Vision analyzer initialized successfully")
        
        print("Testing AutoCheck analyzer...")
        autocheck = AutoCheckAnalyzer()
        assert autocheck is not None
        print("✓ AutoCheck analyzer initialized successfully")
        
        print("Testing notes generator...")
        generator = AINotesGenerator()
        assert generator is not None
        print("✓ Notes generator initialized successfully")
        
        print("\nAll basic tests passed! ✓")
    
    asyncio.run(run_basic_tests())
