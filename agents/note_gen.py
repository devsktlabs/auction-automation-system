
#!/usr/bin/env python3
"""
AI Notes Generation Module
Uses local LLM (Ollama) to generate intelligent notes and insights
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from dataclasses import asdict

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: ollama-python not available. Install with: pip install ollama")

from utils.logger import logger


class AINotesGenerator:
    """
    AI-powered notes generator using local LLM via Ollama
    Generates intelligent insights from vehicle data, vision analysis, and AutoCheck reports
    """
    
    def __init__(self, model_name: str = "llama3.2", ollama_host: str = "http://localhost:11434"):
        self.logger = logger
        self.model_name = model_name
        self.ollama_host = ollama_host
        self.ollama_available = OLLAMA_AVAILABLE
        
        # Fallback to direct API calls if ollama-python not available
        self.session = requests.Session()
        
        # Note generation templates
        self.templates = {
            "vehicle_summary": self._get_vehicle_summary_template(),
            "condition_assessment": self._get_condition_assessment_template(),
            "risk_analysis": self._get_risk_analysis_template(),
            "recommendation": self._get_recommendation_template(),
            "detailed_notes": self._get_detailed_notes_template()
        }
        
        self._test_ollama_connection()
        self.logger.info(f"AI Notes Generator initialized with model: {model_name}")
    
    def _test_ollama_connection(self):
        """Test connection to Ollama server"""
        try:
            if self.ollama_available:
                # Test with ollama-python
                models = ollama.list()
                available_models = [model['name'] for model in models.get('models', [])]
                
                if self.model_name not in available_models:
                    self.logger.warning(f"Model {self.model_name} not found. Available models: {available_models}")
                    # Try to pull the model
                    self.logger.info(f"Attempting to pull model: {self.model_name}")
                    ollama.pull(self.model_name)
                
                self.logger.info("Ollama connection successful")
            else:
                # Test with direct API
                response = self.session.get(f"{self.ollama_host}/api/tags")
                if response.status_code == 200:
                    self.logger.info("Ollama API connection successful")
                else:
                    self.logger.warning(f"Ollama API connection failed: {response.status_code}")
        
        except Exception as e:
            self.logger.warning(f"Could not connect to Ollama: {e}")
    
    async def generate_notes(self, vehicle_data, vision_analysis: Dict[str, Any], 
                           autocheck_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive AI notes from all available data
        
        Args:
            vehicle_data: VehicleData object
            vision_analysis: Results from vision analysis
            autocheck_analysis: Results from AutoCheck analysis
            
        Returns:
            Dictionary containing generated notes and insights
        """
        self.logger.info("Generating AI notes for vehicle analysis")
        
        try:
            # Prepare context data
            context = self._prepare_context(vehicle_data, vision_analysis, autocheck_analysis)
            
            # Generate different types of notes
            notes = {
                "vehicle_summary": await self._generate_vehicle_summary(context),
                "condition_assessment": await self._generate_condition_assessment(context),
                "risk_analysis": await self._generate_risk_analysis(context),
                "key_findings": await self._generate_key_findings(context),
                "recommendations": await self._generate_recommendations(context),
                "detailed_notes": await self._generate_detailed_notes(context),
                "market_insights": await self._generate_market_insights(context),
                "generation_metadata": {
                    "model": self.model_name,
                    "timestamp": datetime.now().isoformat(),
                    "context_size": len(str(context))
                }
            }
            
            self.logger.info("AI notes generation completed successfully")
            return notes
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI notes: {e}")
            return {"error": str(e)}
    
    def _prepare_context(self, vehicle_data, vision_analysis: Dict[str, Any], 
                        autocheck_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context data for AI analysis"""
        context = {
            "vehicle": {
                "vin": getattr(vehicle_data, 'vin', 'Unknown'),
                "year": getattr(vehicle_data, 'year', 0),
                "make": getattr(vehicle_data, 'make', 'Unknown'),
                "model": getattr(vehicle_data, 'model', 'Unknown'),
                "mileage": getattr(vehicle_data, 'mileage', 0),
                "price": getattr(vehicle_data, 'price', 0.0),
                "location": getattr(vehicle_data, 'location', 'Unknown'),
                "condition_grade": getattr(vehicle_data, 'condition_grade', 'Unknown')
            },
            "vision_analysis": vision_analysis,
            "autocheck_analysis": autocheck_analysis,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return context
    
    async def _generate_vehicle_summary(self, context: Dict[str, Any]) -> str:
        """Generate vehicle summary"""
        prompt = self.templates["vehicle_summary"].format(
            year=context["vehicle"]["year"],
            make=context["vehicle"]["make"],
            model=context["vehicle"]["model"],
            mileage=context["vehicle"]["mileage"],
            price=context["vehicle"]["price"],
            vin=context["vehicle"]["vin"]
        )
        
        return await self._query_llm(prompt, max_tokens=200)
    
    async def _generate_condition_assessment(self, context: Dict[str, Any]) -> str:
        """Generate condition assessment"""
        vision_summary = self._summarize_vision_analysis(context["vision_analysis"])
        
        prompt = self.templates["condition_assessment"].format(
            vision_summary=vision_summary,
            vehicle_info=f"{context['vehicle']['year']} {context['vehicle']['make']} {context['vehicle']['model']}"
        )
        
        return await self._query_llm(prompt, max_tokens=300)
    
    async def _generate_risk_analysis(self, context: Dict[str, Any]) -> str:
        """Generate risk analysis"""
        autocheck_summary = self._summarize_autocheck_analysis(context["autocheck_analysis"])
        
        prompt = self.templates["risk_analysis"].format(
            autocheck_summary=autocheck_summary,
            mileage=context["vehicle"]["mileage"],
            year=context["vehicle"]["year"]
        )
        
        return await self._query_llm(prompt, max_tokens=250)
    
    async def _generate_key_findings(self, context: Dict[str, Any]) -> List[str]:
        """Generate key findings as bullet points"""
        prompt = f"""Based on the following vehicle analysis data, identify the top 5-7 key findings that a potential buyer should know:

Vehicle: {context['vehicle']['year']} {context['vehicle']['make']} {context['vehicle']['model']}
Mileage: {context['vehicle']['mileage']:,} miles
Price: ${context['vehicle']['price']:,.2f}

Vision Analysis Summary: {self._summarize_vision_analysis(context['vision_analysis'])}

AutoCheck Summary: {self._summarize_autocheck_analysis(context['autocheck_analysis'])}

Provide key findings as a numbered list, focusing on the most important aspects for a buyer's decision."""
        
        response = await self._query_llm(prompt, max_tokens=300)
        
        # Parse response into list
        findings = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Clean up the line
                clean_line = line.lstrip('0123456789.-• ').strip()
                if clean_line:
                    findings.append(clean_line)
        
        return findings[:7]  # Limit to 7 findings
    
    async def _generate_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations"""
        prompt = f"""As an expert vehicle appraiser, provide recommendations for this vehicle:

Vehicle: {context['vehicle']['year']} {context['vehicle']['make']} {context['vehicle']['model']}
Price: ${context['vehicle']['price']:,.2f}
Mileage: {context['vehicle']['mileage']:,} miles

Analysis Summary:
- Vision Analysis: {self._summarize_vision_analysis(context['vision_analysis'])}
- History Analysis: {self._summarize_autocheck_analysis(context['autocheck_analysis'])}

Provide:
1. Overall recommendation (BUY/CONSIDER/AVOID)
2. Reasoning (2-3 sentences)
3. Suggested actions (if any)
4. Fair market value estimate
5. Negotiation points (if applicable)

Format as clear, actionable advice."""
        
        response = await self._query_llm(prompt, max_tokens=400)
        
        # Parse response into structured format
        recommendations = {
            "overall": "CONSIDER",  # Default
            "reasoning": "",
            "actions": [],
            "market_value": "Unknown",
            "negotiation_points": [],
            "raw_response": response
        }
        
        # Simple parsing - could be enhanced with more sophisticated NLP
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if "BUY" in line.upper() or "RECOMMEND" in line.upper():
                recommendations["overall"] = "BUY"
            elif "AVOID" in line.upper() or "NOT RECOMMEND" in line.upper():
                recommendations["overall"] = "AVOID"
            elif "CONSIDER" in line.upper() or "CAUTION" in line.upper():
                recommendations["overall"] = "CONSIDER"
            
            # Extract reasoning (first substantial paragraph)
            if not recommendations["reasoning"] and len(line) > 50:
                recommendations["reasoning"] = line
        
        return recommendations
    
    async def _generate_detailed_notes(self, context: Dict[str, Any]) -> str:
        """Generate detailed analysis notes"""
        prompt = self.templates["detailed_notes"].format(
            vehicle_context=json.dumps(context["vehicle"], indent=2),
            vision_context=self._summarize_vision_analysis(context["vision_analysis"]),
            autocheck_context=self._summarize_autocheck_analysis(context["autocheck_analysis"])
        )
        
        return await self._query_llm(prompt, max_tokens=500)
    
    async def _generate_market_insights(self, context: Dict[str, Any]) -> str:
        """Generate market insights and value assessment"""
        prompt = f"""Provide market insights for this vehicle:

{context['vehicle']['year']} {context['vehicle']['make']} {context['vehicle']['model']}
Listed Price: ${context['vehicle']['price']:,.2f}
Mileage: {context['vehicle']['mileage']:,} miles

Consider:
- Typical market value for this year/make/model/mileage
- How the condition affects value
- Market demand trends
- Seasonal factors
- Regional considerations

Provide insights on whether the price is fair, high, or low, and explain the reasoning."""
        
        return await self._query_llm(prompt, max_tokens=300)
    
    def _summarize_vision_analysis(self, vision_analysis: Dict[str, Any]) -> str:
        """Create a concise summary of vision analysis"""
        if "error" in vision_analysis:
            return f"Vision analysis error: {vision_analysis['error']}"
        
        summary_parts = []
        
        # Exterior condition
        exterior = vision_analysis.get("exterior_analysis", {})
        if exterior.get("overall_condition"):
            summary_parts.append(f"Exterior: {exterior['overall_condition']}")
        
        # Damage assessment
        damage = vision_analysis.get("damage_assessment", {})
        if damage.get("damage_severity"):
            severity = damage["damage_severity"]
            summary_parts.append(f"Damage severity: {severity}/10")
        
        # Interior condition
        interior = vision_analysis.get("interior_analysis", {})
        if interior.get("overall_condition"):
            summary_parts.append(f"Interior: {interior['overall_condition']}")
        
        # Overall condition
        condition = vision_analysis.get("condition_summary", {})
        if condition.get("overall_condition"):
            summary_parts.append(f"Overall: {condition['overall_condition']}")
        
        return "; ".join(summary_parts) if summary_parts else "No significant findings"
    
    def _summarize_autocheck_analysis(self, autocheck_analysis: Dict[str, Any]) -> str:
        """Create a concise summary of AutoCheck analysis"""
        if "error" in autocheck_analysis:
            return f"AutoCheck error: {autocheck_analysis['error']}"
        
        analysis = autocheck_analysis.get("analysis", {})
        if not analysis:
            return "No AutoCheck data available"
        
        summary_parts = []
        
        # Risk score
        risk_score = analysis.get("risk_score", 0)
        summary_parts.append(f"Risk score: {risk_score}")
        
        # Red flags
        red_flags = analysis.get("red_flags", [])
        if red_flags:
            summary_parts.append(f"{len(red_flags)} red flag(s)")
        
        # Total records
        total_records = analysis.get("total_records", 0)
        summary_parts.append(f"{total_records} history records")
        
        # Overall recommendation
        summary_info = analysis.get("summary", {})
        if summary_info.get("recommendation"):
            summary_parts.append(summary_info["recommendation"])
        
        return "; ".join(summary_parts)
    
    async def _query_llm(self, prompt: str, max_tokens: int = 300) -> str:
        """Query the local LLM via Ollama"""
        try:
            if self.ollama_available:
                # Use ollama-python library
                response = ollama.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={
                        'num_predict': max_tokens,
                        'temperature': 0.7,
                        'top_p': 0.9
                    }
                )
                return response['response'].strip()
            
            else:
                # Use direct API call
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                        "top_p": 0.9
                    },
                    "stream": False
                }
                
                response = self.session.post(
                    f"{self.ollama_host}/api/generate",
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '').strip()
                else:
                    self.logger.error(f"Ollama API error: {response.status_code}")
                    return f"Error: Could not generate response (HTTP {response.status_code})"
        
        except Exception as e:
            self.logger.error(f"LLM query failed: {e}")
            return f"Error: {str(e)}"
    
    def _get_vehicle_summary_template(self) -> str:
        """Template for vehicle summary generation"""
        return """Generate a concise summary for this vehicle listing:

{year} {make} {model}
Mileage: {mileage:,} miles
Price: ${price:,.2f}
VIN: {vin}

Provide a 2-3 sentence summary highlighting the key aspects a buyer should know about this vehicle."""
    
    def _get_condition_assessment_template(self) -> str:
        """Template for condition assessment"""
        return """Based on the visual analysis results, assess the overall condition of this {vehicle_info}:

Visual Analysis Summary: {vision_summary}

Provide a professional assessment of the vehicle's condition, highlighting any concerns or positive aspects."""
    
    def _get_risk_analysis_template(self) -> str:
        """Template for risk analysis"""
        return """Analyze the risk factors for this vehicle based on its history:

AutoCheck Summary: {autocheck_summary}
Vehicle Age: {year}
Mileage: {mileage:,} miles

Identify and explain the key risk factors that could affect the vehicle's value or reliability."""
    
    def _get_recommendation_template(self) -> str:
        """Template for recommendations"""
        return """Provide buying recommendations based on the complete analysis."""
    
    def _get_detailed_notes_template(self) -> str:
        """Template for detailed notes"""
        return """Generate detailed analysis notes for this vehicle:

Vehicle Details:
{vehicle_context}

Visual Analysis:
{vision_context}

History Analysis:
{autocheck_context}

Provide comprehensive notes that would be valuable for a potential buyer or dealer."""


# Example usage and testing
if __name__ == "__main__":
    async def test_notes_generator():
        generator = AINotesGenerator()
        
        # Mock data for testing
        class MockVehicleData:
            def __init__(self):
                self.vin = "1HGBH41JXMN109186"
                self.year = 2021
                self.make = "Honda"
                self.model = "Civic"
                self.mileage = 45000
                self.price = 18500.0
                self.location = "Atlanta, GA"
                self.condition_grade = "Good"
        
        mock_vehicle = MockVehicleData()
        mock_vision = {"exterior_analysis": {"overall_condition": "good"}, "damage_assessment": {"damage_severity": 2}}
        mock_autocheck = {"analysis": {"risk_score": 15, "red_flags": [], "total_records": 8}}
        
        try:
            notes = await generator.generate_notes(mock_vehicle, mock_vision, mock_autocheck)
            print("Generated notes:")
            print(json.dumps(notes, indent=2))
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Run test
    # asyncio.run(test_notes_generator())
    print("AI Notes Generator module loaded successfully")
