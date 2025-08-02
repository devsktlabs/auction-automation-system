
#!/usr/bin/env python3
"""
AutoCheck Report Analysis Module
Parses and analyzes AutoCheck reports (PDF/HTML) for vehicle history
"""

import asyncio
import logging
import re
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pdfplumber
import PyPDF2
from bs4 import BeautifulSoup
from io import BytesIO

from utils.logger import logger


class AutoCheckAnalyzer:
    """
    AutoCheck report parser and analyzer
    Handles both PDF and HTML report formats
    """
    
    def __init__(self):
        self.logger = logger
        self.session = requests.Session()
        self._setup_session()
        
        # Risk indicators and scoring
        self.risk_indicators = {
            "accident": {"weight": 25, "keywords": ["accident", "collision", "crash", "impact"]},
            "flood": {"weight": 30, "keywords": ["flood", "water damage", "submersion"]},
            "fire": {"weight": 35, "keywords": ["fire", "burn", "smoke damage"]},
            "lemon": {"weight": 40, "keywords": ["lemon", "buyback", "manufacturer repurchase"]},
            "theft": {"weight": 20, "keywords": ["theft", "stolen", "recovered"]},
            "hail": {"weight": 15, "keywords": ["hail", "hail damage"]},
            "frame": {"weight": 45, "keywords": ["frame", "structural", "unibody"]},
            "airbag": {"weight": 30, "keywords": ["airbag", "srs", "supplemental restraint"]},
            "odometer": {"weight": 25, "keywords": ["odometer", "mileage", "rollback", "inconsistent"]}
        }
        
        self.logger.info("AutoCheck Analyzer initialized")
    
    def _setup_session(self):
        """Setup requests session for downloading reports"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    async def analyze_report(self, report_url_or_path: str) -> Dict[str, Any]:
        """
        Analyze AutoCheck report from URL or local file path
        
        Args:
            report_url_or_path: URL to AutoCheck report or local file path
            
        Returns:
            Dictionary containing parsed report data and analysis
        """
        self.logger.info(f"Analyzing AutoCheck report: {report_url_or_path}")
        
        try:
            # Determine if input is URL or file path
            if report_url_or_path.startswith(('http://', 'https://')):
                report_data = await self._download_and_parse_report(report_url_or_path)
            else:
                report_data = await self._parse_local_report(report_url_or_path)
            
            # Analyze the parsed data
            analysis = await self._analyze_report_data(report_data)
            
            return {
                "report_source": report_url_or_path,
                "parsed_data": report_data,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze AutoCheck report: {e}")
            return {"error": str(e), "report_source": report_url_or_path}
    
    async def _download_and_parse_report(self, url: str) -> Dict[str, Any]:
        """Download and parse AutoCheck report from URL"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'pdf' in content_type:
                return await self._parse_pdf_content(BytesIO(response.content))
            else:
                return await self._parse_html_content(response.text)
                
        except Exception as e:
            self.logger.error(f"Failed to download report from {url}: {e}")
            raise
    
    async def _parse_local_report(self, file_path: str) -> Dict[str, Any]:
        """Parse local AutoCheck report file"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Report file not found: {file_path}")
        
        if path.suffix.lower() == '.pdf':
            with open(path, 'rb') as f:
                return await self._parse_pdf_content(f)
        else:
            with open(path, 'r', encoding='utf-8') as f:
                return await self._parse_html_content(f.read())
    
    async def _parse_pdf_content(self, pdf_file) -> Dict[str, Any]:
        """Parse PDF AutoCheck report"""
        parsed_data = {
            "format": "pdf",
            "vehicle_info": {},
            "history_records": [],
            "summary_scores": {},
            "raw_text": ""
        }
        
        try:
            # Try pdfplumber first (better for structured data)
            with pdfplumber.open(pdf_file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                
                parsed_data["raw_text"] = full_text
                
                # Extract structured data
                parsed_data["vehicle_info"] = self._extract_vehicle_info_from_text(full_text)
                parsed_data["history_records"] = self._extract_history_records_from_text(full_text)
                parsed_data["summary_scores"] = self._extract_summary_scores_from_text(full_text)
                
                # Try to extract tables
                tables = []
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
                
                if tables:
                    parsed_data["tables"] = tables
                    parsed_data["history_records"].extend(self._parse_tables_for_history(tables))
            
        except Exception as e:
            self.logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
            
            # Fallback to PyPDF2
            try:
                pdf_file.seek(0)  # Reset file pointer
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                full_text = ""
                for page in pdf_reader.pages:
                    full_text += page.extract_text() + "\n"
                
                parsed_data["raw_text"] = full_text
                parsed_data["vehicle_info"] = self._extract_vehicle_info_from_text(full_text)
                parsed_data["history_records"] = self._extract_history_records_from_text(full_text)
                
            except Exception as e2:
                self.logger.error(f"Both PDF parsers failed: {e2}")
                parsed_data["error"] = f"PDF parsing failed: {e2}"
        
        return parsed_data
    
    async def _parse_html_content(self, html_content: str) -> Dict[str, Any]:
        """Parse HTML AutoCheck report"""
        parsed_data = {
            "format": "html",
            "vehicle_info": {},
            "history_records": [],
            "summary_scores": {},
            "raw_text": ""
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract text content
            parsed_data["raw_text"] = soup.get_text()
            
            # Extract vehicle information
            parsed_data["vehicle_info"] = self._extract_vehicle_info_from_html(soup)
            
            # Extract history records
            parsed_data["history_records"] = self._extract_history_records_from_html(soup)
            
            # Extract summary scores
            parsed_data["summary_scores"] = self._extract_summary_scores_from_html(soup)
            
        except Exception as e:
            self.logger.error(f"HTML parsing failed: {e}")
            parsed_data["error"] = f"HTML parsing failed: {e}"
        
        return parsed_data
    
    def _extract_vehicle_info_from_text(self, text: str) -> Dict[str, Any]:
        """Extract vehicle information from text"""
        vehicle_info = {}
        
        # VIN extraction
        vin_pattern = r'\b[A-HJ-NPR-Z0-9]{17}\b'
        vin_match = re.search(vin_pattern, text)
        if vin_match:
            vehicle_info["vin"] = vin_match.group()
        
        # Year extraction
        year_pattern = r'\b(19|20)\d{2}\b'
        year_matches = re.findall(year_pattern, text)
        if year_matches:
            # Take the most likely year (usually the first one that makes sense for a vehicle)
            years = [int(y) for y in year_matches if 1980 <= int(y) <= datetime.now().year + 1]
            if years:
                vehicle_info["year"] = min(years)  # Usually the model year
        
        # Make and model extraction (basic pattern matching)
        make_model_patterns = [
            r'(TOYOTA|HONDA|FORD|CHEVROLET|NISSAN|BMW|MERCEDES|AUDI|VOLKSWAGEN|HYUNDAI|KIA|MAZDA|SUBARU|LEXUS|ACURA|INFINITI|CADILLAC|BUICK|GMC|JEEP|CHRYSLER|DODGE|RAM|LINCOLN|VOLVO|JAGUAR|LAND ROVER|PORSCHE|TESLA|MITSUBISHI)\s+([A-Z][A-Z0-9\s]+)',
            r'Make:\s*([A-Z][A-Za-z]+)',
            r'Model:\s*([A-Z][A-Za-z0-9\s]+)'
        ]
        
        for pattern in make_model_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    vehicle_info["make"] = match.group(1).title()
                    vehicle_info["model"] = match.group(2).strip().title()
                else:
                    if "make" not in vehicle_info:
                        vehicle_info["make"] = match.group(1).title()
                break
        
        return vehicle_info
    
    def _extract_history_records_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract history records from text"""
        records = []
        
        # Look for date patterns and associated events
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})'
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            date_match = re.search(date_pattern, line)
            if date_match:
                record = {
                    "date": date_match.group(1),
                    "event": line.strip(),
                    "risk_level": "unknown"
                }
                
                # Check surrounding lines for more context
                context_lines = lines[max(0, i-1):min(len(lines), i+3)]
                context = " ".join(context_lines).lower()
                
                # Classify risk level based on keywords
                for risk_type, risk_info in self.risk_indicators.items():
                    if any(keyword in context for keyword in risk_info["keywords"]):
                        record["risk_level"] = risk_type
                        record["risk_weight"] = risk_info["weight"]
                        break
                
                records.append(record)
        
        return records
    
    def _extract_summary_scores_from_text(self, text: str) -> Dict[str, Any]:
        """Extract summary scores from text"""
        scores = {}
        
        # Look for AutoCheck Score
        score_patterns = [
            r'AutoCheck\s+Score[:\s]+(\d+)',
            r'Score[:\s]+(\d+)\s*(?:out of|/)\s*(\d+)',
            r'Overall\s+Score[:\s]+(\d+)'
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores["autocheck_score"] = int(match.group(1))
                if len(match.groups()) > 1:
                    scores["max_score"] = int(match.group(2))
                break
        
        # Look for number of records
        records_pattern = r'(\d+)\s+(?:records?|events?|entries)'
        records_match = re.search(records_pattern, text, re.IGNORECASE)
        if records_match:
            scores["total_records"] = int(records_match.group(1))
        
        return scores
    
    def _extract_vehicle_info_from_html(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract vehicle information from HTML"""
        vehicle_info = {}
        
        # Look for common HTML patterns in AutoCheck reports
        # VIN
        vin_selectors = ['[data-vin]', '.vin', '#vin', '[class*="vin"]']
        for selector in vin_selectors:
            element = soup.select_one(selector)
            if element:
                vin_text = element.get_text().strip()
                vin_match = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', vin_text)
                if vin_match:
                    vehicle_info["vin"] = vin_match.group()
                    break
        
        # Year, Make, Model
        vehicle_selectors = ['.vehicle-info', '.vehicle-details', '[class*="vehicle"]']
        for selector in vehicle_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                info = self._extract_vehicle_info_from_text(text)
                vehicle_info.update(info)
                break
        
        return vehicle_info
    
    def _extract_history_records_from_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract history records from HTML"""
        records = []
        
        # Look for tables or lists containing history
        table_selectors = ['table', '.history-table', '.records-table']
        for selector in table_selectors:
            tables = soup.select(selector)
            for table in tables:
                table_records = self._parse_html_table_for_history(table)
                records.extend(table_records)
        
        # Look for list items
        list_selectors = ['.history-list li', '.records-list li', 'ul li']
        for selector in list_selectors:
            items = soup.select(selector)
            for item in items:
                text = item.get_text().strip()
                if self._looks_like_history_record(text):
                    record = {
                        "event": text,
                        "risk_level": "unknown"
                    }
                    
                    # Classify risk
                    text_lower = text.lower()
                    for risk_type, risk_info in self.risk_indicators.items():
                        if any(keyword in text_lower for keyword in risk_info["keywords"]):
                            record["risk_level"] = risk_type
                            record["risk_weight"] = risk_info["weight"]
                            break
                    
                    records.append(record)
        
        return records
    
    def _extract_summary_scores_from_html(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract summary scores from HTML"""
        scores = {}
        
        # Look for score elements
        score_selectors = ['.score', '.autocheck-score', '[class*="score"]']
        for selector in score_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text()
                score_match = re.search(r'(\d+)', text)
                if score_match:
                    scores["autocheck_score"] = int(score_match.group(1))
                    break
        
        return scores
    
    def _parse_tables_for_history(self, tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
        """Parse tables for history records"""
        records = []
        
        for table in tables:
            if not table:
                continue
            
            # Assume first row might be headers
            headers = table[0] if table else []
            
            for row in table[1:]:
                if len(row) >= 2:  # Need at least date and event
                    record = {
                        "date": row[0] if row[0] else "unknown",
                        "event": " ".join(row[1:]) if len(row) > 1 else row[0],
                        "risk_level": "unknown"
                    }
                    
                    # Classify risk
                    event_text = record["event"].lower()
                    for risk_type, risk_info in self.risk_indicators.items():
                        if any(keyword in event_text for keyword in risk_info["keywords"]):
                            record["risk_level"] = risk_type
                            record["risk_weight"] = risk_info["weight"]
                            break
                    
                    records.append(record)
        
        return records
    
    def _parse_html_table_for_history(self, table) -> List[Dict[str, Any]]:
        """Parse HTML table for history records"""
        records = []
        
        rows = table.select('tr')
        for row in rows[1:]:  # Skip header row
            cells = row.select('td, th')
            if len(cells) >= 2:
                record = {
                    "date": cells[0].get_text().strip(),
                    "event": " ".join(cell.get_text().strip() for cell in cells[1:]),
                    "risk_level": "unknown"
                }
                
                # Classify risk
                event_text = record["event"].lower()
                for risk_type, risk_info in self.risk_indicators.items():
                    if any(keyword in event_text for keyword in risk_info["keywords"]):
                        record["risk_level"] = risk_type
                        record["risk_weight"] = risk_info["weight"]
                        break
                
                records.append(record)
        
        return records
    
    def _looks_like_history_record(self, text: str) -> bool:
        """Check if text looks like a history record"""
        # Simple heuristics to identify history records
        date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
        has_date = bool(re.search(date_pattern, text))
        
        # Check for common history keywords
        history_keywords = ["registration", "title", "inspection", "service", "accident", "damage", "repair"]
        has_history_keyword = any(keyword in text.lower() for keyword in history_keywords)
        
        return has_date or has_history_keyword
    
    async def _analyze_report_data(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze parsed report data and generate insights"""
        analysis = {
            "risk_score": 0,
            "risk_factors": [],
            "red_flags": [],
            "positive_indicators": [],
            "summary": {},
            "recommendations": []
        }
        
        try:
            # Analyze history records
            history_records = report_data.get("history_records", [])
            analysis["total_records"] = len(history_records)
            
            # Calculate risk score
            total_risk_weight = 0
            risk_counts = {}
            
            for record in history_records:
                risk_level = record.get("risk_level", "unknown")
                risk_weight = record.get("risk_weight", 0)
                
                if risk_level != "unknown":
                    total_risk_weight += risk_weight
                    risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
                    
                    analysis["risk_factors"].append({
                        "type": risk_level,
                        "event": record.get("event", ""),
                        "date": record.get("date", ""),
                        "weight": risk_weight
                    })
            
            analysis["risk_score"] = min(100, total_risk_weight)  # Cap at 100
            analysis["risk_counts"] = risk_counts
            
            # Identify red flags (high-risk items)
            high_risk_threshold = 25
            for risk_factor in analysis["risk_factors"]:
                if risk_factor["weight"] >= high_risk_threshold:
                    analysis["red_flags"].append(
                        f"{risk_factor['type'].title()}: {risk_factor['event']}"
                    )
            
            # Identify positive indicators
            if analysis["total_records"] > 0 and analysis["risk_score"] < 20:
                analysis["positive_indicators"].append("Clean history with minimal risk factors")
            
            if "service" in risk_counts and risk_counts["service"] > 2:
                analysis["positive_indicators"].append("Regular maintenance records found")
            
            # Generate summary
            analysis["summary"] = {
                "overall_risk": self._categorize_risk_level(analysis["risk_score"]),
                "major_concerns": len(analysis["red_flags"]),
                "total_events": analysis["total_records"],
                "recommendation": self._generate_recommendation(analysis)
            }
            
            # Generate specific recommendations
            analysis["recommendations"] = self._generate_detailed_recommendations(analysis, risk_counts)
            
        except Exception as e:
            self.logger.error(f"Error analyzing report data: {e}")
            analysis["error"] = str(e)
        
        return analysis
    
    def _categorize_risk_level(self, risk_score: float) -> str:
        """Categorize risk level based on score"""
        if risk_score < 10:
            return "very_low"
        elif risk_score < 25:
            return "low"
        elif risk_score < 50:
            return "moderate"
        elif risk_score < 75:
            return "high"
        else:
            return "very_high"
    
    def _generate_recommendation(self, analysis: Dict[str, Any]) -> str:
        """Generate overall recommendation"""
        risk_score = analysis["risk_score"]
        red_flags_count = len(analysis["red_flags"])
        
        if risk_score < 10 and red_flags_count == 0:
            return "RECOMMENDED - Clean history"
        elif risk_score < 25 and red_flags_count <= 1:
            return "ACCEPTABLE - Minor history issues"
        elif risk_score < 50:
            return "CAUTION - Moderate risk factors present"
        else:
            return "AVOID - High risk vehicle"
    
    def _generate_detailed_recommendations(self, analysis: Dict[str, Any], 
                                         risk_counts: Dict[str, int]) -> List[str]:
        """Generate detailed recommendations based on analysis"""
        recommendations = []
        
        # Accident-related recommendations
        if "accident" in risk_counts:
            count = risk_counts["accident"]
            if count == 1:
                recommendations.append("Single accident reported - verify repair quality")
            else:
                recommendations.append(f"Multiple accidents ({count}) - thorough inspection required")
        
        # Flood damage recommendations
        if "flood" in risk_counts:
            recommendations.append("Flood damage reported - check for electrical and mechanical issues")
        
        # Frame damage recommendations
        if "frame" in risk_counts:
            recommendations.append("Frame damage reported - structural integrity assessment needed")
        
        # Odometer issues
        if "odometer" in risk_counts:
            recommendations.append("Odometer inconsistencies - verify actual mileage")
        
        # General recommendations based on risk score
        risk_score = analysis["risk_score"]
        if risk_score > 50:
            recommendations.append("Consider professional pre-purchase inspection")
        
        if analysis["total_records"] > 15:
            recommendations.append("High number of records - review detailed history")
        
        return recommendations


# Example usage and testing
if __name__ == "__main__":
    async def test_autocheck_analyzer():
        analyzer = AutoCheckAnalyzer()
        
        # Test with sample report (replace with actual path/URL)
        test_report = "/path/to/autocheck_report.pdf"
        
        try:
            results = await analyzer.analyze_report(test_report)
            print("AutoCheck analysis results:")
            print(json.dumps(results, indent=2, default=str))
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Run test
    # asyncio.run(test_autocheck_analyzer())
    print("AutoCheck Analyzer module loaded successfully")
