
#!/usr/bin/env python3
"""
CarMax AI Agent - Comprehensive local AI agent for carmaxauctions.com
Replicates ChatGPT agent capabilities for vehicle analysis and report generation
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from fake_useragent import UserAgent

from .vision import VehicleVisionAnalyzer
from .autocheck import AutoCheckAnalyzer
from .note_gen import AINotesGenerator
from utils.logger import logger
from utils.config import config
from utils.rate_limiter import RateLimiter


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


@dataclass
class AnalysisResult:
    """Complete analysis result for a vehicle"""
    vehicle_data: VehicleData
    vision_analysis: Dict[str, Any]
    autocheck_analysis: Dict[str, Any]
    ai_notes: Dict[str, Any]
    red_flags: List[str]
    condition_score: float
    recommendation: str
    timestamp: str
    processing_time: float


class CarMaxAIAgent:
    """
    Comprehensive AI agent for CarMax auctions analysis
    Integrates web scraping, vision analysis, autocheck parsing, and AI note generation
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = config
        self.logger = logger
        # Initialize rate limiter with config
        from utils.rate_limiter import RateLimiter, RateLimitConfig
        self.rate_limiter = RateLimiter()
        self.rate_limit_config = RateLimitConfig(
            requests_per_minute=30,
            burst_limit=5,
            cooldown_seconds=10
        )
        
        # Initialize AI components
        self.vision_analyzer = VehicleVisionAnalyzer()
        self.autocheck_analyzer = AutoCheckAnalyzer()
        self.notes_generator = AINotesGenerator()
        
        # Web scraping setup
        self.session = requests.Session()
        self.ua = UserAgent()
        self._setup_session()
        
        # Driver for JavaScript-heavy pages
        self.driver = None
        self._setup_driver()
        
        # Output directories
        self.output_dir = Path(config.get('output_dir', './data/carmax_analysis'))
        self.images_dir = self.output_dir / 'images'
        self.reports_dir = self.output_dir / 'reports'
        self._create_directories()
        
        self.logger.info("CarMax AI Agent initialized successfully")
    
    def _setup_session(self):
        """Configure requests session with headers and settings"""
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def _setup_driver(self):
        """Setup undetected Chrome driver for JavaScript rendering"""
        try:
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'--user-agent={self.ua.random}')
            
            self.driver = uc.Chrome(options=options)
            self.logger.info("Chrome driver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            self.driver = None
    
    def _create_directories(self):
        """Create necessary output directories"""
        for directory in [self.output_dir, self.images_dir, self.reports_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def analyze_vehicle(self, url: str) -> AnalysisResult:
        """
        Complete analysis pipeline for a single vehicle
        
        Args:
            url: CarMax auction URL for the vehicle
            
        Returns:
            AnalysisResult with complete analysis
        """
        start_time = time.time()
        self.logger.info(f"Starting analysis for vehicle: {url}")
        
        try:
            # Step 1: Scrape vehicle data and images
            vehicle_data = await self._scrape_vehicle_data(url)
            
            # Step 2: Download and analyze images
            vision_analysis = await self._analyze_vehicle_images(vehicle_data)
            
            # Step 3: Parse AutoCheck report if available
            autocheck_analysis = await self._analyze_autocheck_report(vehicle_data)
            
            # Step 4: Generate AI notes and recommendations
            ai_notes = await self._generate_ai_notes(vehicle_data, vision_analysis, autocheck_analysis)
            
            # Step 5: Calculate condition score and extract red flags
            condition_score, red_flags = self._calculate_condition_score(
                vehicle_data, vision_analysis, autocheck_analysis
            )
            
            # Step 6: Generate final recommendation
            recommendation = self._generate_recommendation(condition_score, red_flags, ai_notes)
            
            processing_time = time.time() - start_time
            
            result = AnalysisResult(
                vehicle_data=vehicle_data,
                vision_analysis=vision_analysis,
                autocheck_analysis=autocheck_analysis,
                ai_notes=ai_notes,
                red_flags=red_flags,
                condition_score=condition_score,
                recommendation=recommendation,
                timestamp=datetime.now().isoformat(),
                processing_time=processing_time
            )
            
            # Save results
            await self._save_analysis_result(result)
            
            self.logger.info(f"Analysis completed in {processing_time:.2f}s for {url}")
            return result
            
        except Exception as e:
            self.logger.error(f"Analysis failed for {url}: {e}")
            raise
    
    async def _scrape_vehicle_data(self, url: str) -> VehicleData:
        """Scrape vehicle data from CarMax auction page"""
        self.logger.info(f"Scraping vehicle data from: {url}")
        
        # Rate limiting
        await self.rate_limiter.async_wait_if_needed("carmax_scraping", self.rate_limit_config)
        
        vehicle_data = VehicleData(url=url)
        
        try:
            if self.driver:
                # Use Selenium for JavaScript-heavy pages
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Extract vehicle information
                vehicle_data = await self._extract_vehicle_info_selenium(vehicle_data)
                
                # Extract image URLs
                vehicle_data.images = await self._extract_image_urls_selenium()
                
            else:
                # Fallback to requests + BeautifulSoup
                response = self.session.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                vehicle_data = await self._extract_vehicle_info_bs4(vehicle_data, soup)
                vehicle_data.images = await self._extract_image_urls_bs4(soup)
            
            self.logger.info(f"Successfully scraped data for {vehicle_data.make} {vehicle_data.model}")
            return vehicle_data
            
        except Exception as e:
            self.logger.error(f"Failed to scrape vehicle data: {e}")
            raise
    
    async def _extract_vehicle_info_selenium(self, vehicle_data: VehicleData) -> VehicleData:
        """Extract vehicle information using Selenium"""
        try:
            # VIN
            try:
                vin_element = self.driver.find_element(By.XPATH, "//span[contains(text(), 'VIN')]/following-sibling::span")
                vehicle_data.vin = vin_element.text.strip()
            except NoSuchElementException:
                pass
            
            # Year, Make, Model
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR, "h1, .vehicle-title, .listing-title")
                title_parts = title_element.text.strip().split()
                if len(title_parts) >= 3:
                    vehicle_data.year = int(title_parts[0])
                    vehicle_data.make = title_parts[1]
                    vehicle_data.model = " ".join(title_parts[2:])
            except (NoSuchElementException, ValueError):
                pass
            
            # Mileage
            try:
                mileage_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'miles') or contains(text(), 'Mileage')]")
                mileage_text = mileage_element.text
                mileage_numbers = ''.join(filter(str.isdigit, mileage_text))
                if mileage_numbers:
                    vehicle_data.mileage = int(mileage_numbers)
            except (NoSuchElementException, ValueError):
                pass
            
            # Price
            try:
                price_element = self.driver.find_element(By.CSS_SELECTOR, ".price, .current-price, [class*='price']")
                price_text = price_element.text
                price_numbers = ''.join(c for c in price_text if c.isdigit() or c == '.')
                if price_numbers:
                    vehicle_data.price = float(price_numbers)
            except (NoSuchElementException, ValueError):
                pass
            
            return vehicle_data
            
        except Exception as e:
            self.logger.error(f"Error extracting vehicle info with Selenium: {e}")
            return vehicle_data
    
    async def _extract_image_urls_selenium(self) -> List[str]:
        """Extract image URLs using Selenium"""
        image_urls = []
        try:
            # Look for various image selectors
            selectors = [
                "img[src*='vehicle']",
                "img[src*='car']",
                ".vehicle-image img",
                ".gallery img",
                ".carousel img"
            ]
            
            for selector in selectors:
                try:
                    images = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for img in images:
                        src = img.get_attribute('src')
                        if src and src.startswith('http'):
                            image_urls.append(src)
                except NoSuchElementException:
                    continue
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in image_urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            self.logger.info(f"Found {len(unique_urls)} vehicle images")
            return unique_urls
            
        except Exception as e:
            self.logger.error(f"Error extracting image URLs: {e}")
            return []
    
    async def _extract_vehicle_info_bs4(self, vehicle_data: VehicleData, soup: BeautifulSoup) -> VehicleData:
        """Extract vehicle information using BeautifulSoup (fallback)"""
        # Implementation for BeautifulSoup extraction
        # This is a simplified version - would need to be customized for actual CarMax HTML structure
        return vehicle_data
    
    async def _extract_image_urls_bs4(self, soup: BeautifulSoup) -> List[str]:
        """Extract image URLs using BeautifulSoup (fallback)"""
        # Implementation for BeautifulSoup image extraction
        return []
    
    async def _analyze_vehicle_images(self, vehicle_data: VehicleData) -> Dict[str, Any]:
        """Analyze vehicle images using local vision models"""
        if not vehicle_data.images:
            return {"error": "No images available for analysis"}
        
        # Download images locally
        local_image_paths = await self._download_images(vehicle_data)
        
        # Analyze with vision model
        vision_analysis = await self.vision_analyzer.analyze_vehicle_images(local_image_paths)
        
        return vision_analysis
    
    async def _download_images(self, vehicle_data: VehicleData) -> List[str]:
        """Download vehicle images locally for analysis"""
        local_paths = []
        vehicle_dir = self.images_dir / f"{vehicle_data.vin or 'unknown'}_{int(time.time())}"
        vehicle_dir.mkdir(exist_ok=True)
        
        for i, image_url in enumerate(vehicle_data.images[:20]):  # Limit to 20 images
            try:
                response = self.session.get(image_url, timeout=30)
                response.raise_for_status()
                
                # Determine file extension
                content_type = response.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                else:
                    ext = '.jpg'  # Default
                
                local_path = vehicle_dir / f"image_{i:02d}{ext}"
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                local_paths.append(str(local_path))
                
            except Exception as e:
                self.logger.warning(f"Failed to download image {image_url}: {e}")
                continue
        
        self.logger.info(f"Downloaded {len(local_paths)} images to {vehicle_dir}")
        return local_paths
    
    async def _analyze_autocheck_report(self, vehicle_data: VehicleData) -> Dict[str, Any]:
        """Analyze AutoCheck report if available"""
        if not vehicle_data.autocheck_url:
            return {"error": "No AutoCheck report URL available"}
        
        return await self.autocheck_analyzer.analyze_report(vehicle_data.autocheck_url)
    
    async def _generate_ai_notes(self, vehicle_data: VehicleData, vision_analysis: Dict[str, Any], 
                                autocheck_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered notes and insights"""
        return await self.notes_generator.generate_notes(
            vehicle_data, vision_analysis, autocheck_analysis
        )
    
    def _calculate_condition_score(self, vehicle_data: VehicleData, vision_analysis: Dict[str, Any],
                                 autocheck_analysis: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Calculate overall condition score and identify red flags"""
        score = 100.0  # Start with perfect score
        red_flags = []
        
        # Vision analysis penalties
        if 'damage_detected' in vision_analysis:
            damage_severity = vision_analysis.get('damage_severity', 0)
            score -= damage_severity * 10
            if damage_severity > 5:
                red_flags.append(f"Significant damage detected (severity: {damage_severity})")
        
        # AutoCheck penalties
        if 'accidents' in autocheck_analysis:
            accident_count = autocheck_analysis.get('accident_count', 0)
            score -= accident_count * 15
            if accident_count > 0:
                red_flags.append(f"{accident_count} accident(s) reported")
        
        # Mileage considerations
        if vehicle_data.year and vehicle_data.mileage:
            age = datetime.now().year - vehicle_data.year
            expected_mileage = age * 12000  # 12k miles per year average
            if vehicle_data.mileage > expected_mileage * 1.5:
                score -= 20
                red_flags.append("High mileage for vehicle age")
        
        return max(0.0, min(100.0, score)), red_flags
    
    def _generate_recommendation(self, condition_score: float, red_flags: List[str], 
                               ai_notes: Dict[str, Any]) -> str:
        """Generate final recommendation based on analysis"""
        if condition_score >= 80 and not red_flags:
            return "RECOMMENDED - Excellent condition vehicle"
        elif condition_score >= 60 and len(red_flags) <= 2:
            return "CONSIDER - Good condition with minor issues"
        elif condition_score >= 40:
            return "CAUTION - Multiple issues identified"
        else:
            return "AVOID - Significant problems detected"
    
    async def _save_analysis_result(self, result: AnalysisResult):
        """Save analysis result to files"""
        vehicle_id = result.vehicle_data.vin or f"unknown_{int(time.time())}"
        
        # Save JSON report
        json_path = self.reports_dir / f"{vehicle_id}_analysis.json"
        with open(json_path, 'w') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        
        # Save markdown report
        md_path = self.reports_dir / f"{vehicle_id}_report.md"
        await self._generate_markdown_report(result, md_path)
        
        self.logger.info(f"Analysis results saved to {json_path} and {md_path}")
    
    async def _generate_markdown_report(self, result: AnalysisResult, output_path: Path):
        """Generate human-readable markdown report"""
        vehicle = result.vehicle_data
        
        report = f"""# Vehicle Analysis Report
        
## Vehicle Information
- **VIN:** {vehicle.vin}
- **Year:** {vehicle.year}
- **Make:** {vehicle.make}
- **Model:** {vehicle.model}
- **Mileage:** {vehicle.mileage:,} miles
- **Price:** ${vehicle.price:,.2f}
- **URL:** {vehicle.url}

## Analysis Summary
- **Condition Score:** {result.condition_score:.1f}/100
- **Recommendation:** {result.recommendation}
- **Processing Time:** {result.processing_time:.2f} seconds
- **Analysis Date:** {result.timestamp}

## Red Flags
{chr(10).join(f"- {flag}" for flag in result.red_flags) if result.red_flags else "None identified"}

## Vision Analysis
{self._format_vision_analysis(result.vision_analysis)}

## AutoCheck Analysis
{self._format_autocheck_analysis(result.autocheck_analysis)}

## AI Generated Notes
{self._format_ai_notes(result.ai_notes)}
"""
        
        with open(output_path, 'w') as f:
            f.write(report)
    
    def _format_vision_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format vision analysis for markdown report"""
        if 'error' in analysis:
            return f"Error: {analysis['error']}"
        
        sections = []
        for key, value in analysis.items():
            if isinstance(value, dict):
                sections.append(f"### {key.replace('_', ' ').title()}")
                for subkey, subvalue in value.items():
                    sections.append(f"- **{subkey.replace('_', ' ').title()}:** {subvalue}")
            else:
                sections.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        
        return '\n'.join(sections)
    
    def _format_autocheck_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format AutoCheck analysis for markdown report"""
        if 'error' in analysis:
            return f"Error: {analysis['error']}"
        
        return "AutoCheck analysis results would be formatted here"
    
    def _format_ai_notes(self, notes: Dict[str, Any]) -> str:
        """Format AI notes for markdown report"""
        if 'error' in notes:
            return f"Error: {notes['error']}"
        
        return "AI-generated notes would be formatted here"
    
    async def batch_analyze(self, urls: List[str], max_concurrent: int = 3) -> List[AnalysisResult]:
        """
        Analyze multiple vehicles concurrently
        
        Args:
            urls: List of CarMax auction URLs
            max_concurrent: Maximum number of concurrent analyses
            
        Returns:
            List of AnalysisResult objects
        """
        self.logger.info(f"Starting batch analysis of {len(urls)} vehicles")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(url):
            async with semaphore:
                try:
                    return await self.analyze_vehicle(url)
                except Exception as e:
                    self.logger.error(f"Failed to analyze {url}: {e}")
                    return None
        
        tasks = [analyze_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        valid_results = [r for r in results if isinstance(r, AnalysisResult)]
        
        self.logger.info(f"Batch analysis completed: {len(valid_results)}/{len(urls)} successful")
        return valid_results
    
    def __del__(self):
        """Cleanup resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


# Example usage and testing
if __name__ == "__main__":
    async def main():
        agent = CarMaxAIAgent()
        
        # Test with a sample URL (replace with actual CarMax auction URL)
        test_url = "https://carmaxauctions.com/vehicle/12345"
        
        try:
            result = await agent.analyze_vehicle(test_url)
            print(f"Analysis completed: {result.recommendation}")
            print(f"Condition Score: {result.condition_score}")
            print(f"Red Flags: {result.red_flags}")
        except Exception as e:
            print(f"Analysis failed: {e}")
    
    # Run the test
    # asyncio.run(main())
    print("CarMax AI Agent module loaded successfully")
