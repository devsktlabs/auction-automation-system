
import requests
import time
import random
from typing import Dict, Optional
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from automation.browser import StealthBrowser
from utils.config import config
from utils.logger import logger
from utils.rate_limiter import rate_limiter, RateLimitConfig
from utils.errors import IntegrationError

class AutoCheckIntegrator:
    """AutoCheck vehicle history integration"""
    
    def __init__(self):
        self.api_key = config.get_integration_config('autocheck').get('api_key')
        self.fallback_scraping = config.get_integration_config('autocheck').get('fallback_scraping', True)
        self.session = requests.Session()
        self.browser = None
        self.rate_config = RateLimitConfig(
            requests_per_minute=8,
            burst_limit=2,
            cooldown_seconds=8
        )
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def get_vehicle_history(self, vin: str) -> Dict[str, any]:
        """Get AutoCheck vehicle history report"""
        try:
            # Try API first if available
            if self.api_key:
                api_result = self._get_history_api(vin)
                if api_result:
                    return api_result
            
            # Fallback to scraping
            if self.fallback_scraping:
                return self._get_history_scraping(vin)
            
            return {}
            
        except Exception as e:
            logger.error(f"AutoCheck history lookup failed for {vin}: {e}")
            return {}
    
    def _get_history_api(self, vin: str) -> Optional[Dict[str, any]]:
        """Get history using AutoCheck API"""
        try:
            url = f"https://api.autocheck.com/v1/vehicle/{vin}/history"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("AutoCheck API rate limit exceeded")
                return None
            else:
                logger.warning(f"AutoCheck API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"AutoCheck API request failed: {e}")
            return None
    
    def _get_history_scraping(self, vin: str) -> Dict[str, any]:
        """Get history using web scraping"""
        try:
            # Rate limiting
            rate_limiter.wait_if_needed('autocheck', self.rate_config)
            
            if not self.browser:
                self.browser = StealthBrowser("autocheck")
                self.driver = self.browser.create_stealth_driver()
            
            # Navigate to AutoCheck VIN lookup
            url = f"https://www.autocheck.com/vehiclehistory/autocheck/en/vinbasics?vin={vin}"
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(random.uniform(3, 6))
            
            # Extract summary data
            summary = self._extract_autocheck_summary()
            
            # Record request for rate limiting
            rate_limiter.record_request('autocheck')
            
            return {
                'vin': vin,
                'source': 'autocheck_scraping',
                'summary': summary,
                'report_url': url
            }
            
        except Exception as e:
            logger.error(f"AutoCheck scraping failed for {vin}: {e}")
            return {}
    
    def _extract_autocheck_summary(self) -> Dict[str, any]:
        """Extract key information from AutoCheck page"""
        summary = {}
        
        try:
            # AutoCheck Score
            try:
                score_element = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".autocheck-score"
                )
                summary['autocheck_score'] = score_element.text.strip()
            except NoSuchElementException:
                summary['autocheck_score'] = None
            
            # Accident/Damage records
            try:
                accident_element = self.driver.find_element(
                    By.XPATH,
                    "//span[contains(text(), 'Accident')]/following-sibling::span"
                )
                summary['accident_damage_records'] = accident_element.text.strip()
            except NoSuchElementException:
                summary['accident_damage_records'] = "0"
            
            # Title information
            try:
                title_element = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".title-info"
                )
                summary['title_info'] = title_element.text.strip()
            except NoSuchElementException:
                summary['title_info'] = "Clean"
            
            # Odometer readings
            odometer_readings = []
            try:
                odometer_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".odometer-reading"
                )
                for element in odometer_elements:
                    reading = element.text.strip()
                    if reading:
                        odometer_readings.append(reading)
            except NoSuchElementException:
                pass
            
            summary['odometer_readings'] = odometer_readings
            
            # Vehicle use (Personal, Commercial, etc.)
            try:
                use_element = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".vehicle-use"
                )
                summary['vehicle_use'] = use_element.text.strip()
            except NoSuchElementException:
                summary['vehicle_use'] = "Unknown"
            
        except Exception as e:
            logger.error(f"AutoCheck summary extraction failed: {e}")
        
        return summary
    
    def analyze_autocheck_score(self, history_data: Dict[str, any]) -> Dict[str, any]:
        """Analyze AutoCheck score and provide recommendations"""
        analysis = {
            'score_interpretation': 'unknown',
            'recommendations': [],
            'risk_level': 'unknown'
        }
        
        try:
            summary = history_data.get('summary', {})
            score_text = summary.get('autocheck_score', '')
            
            # Extract numeric score if present
            score = None
            if score_text:
                import re
                score_match = re.search(r'(\d+)', score_text)
                if score_match:
                    score = int(score_match.group(1))
            
            if score:
                if score >= 90:
                    analysis['score_interpretation'] = 'excellent'
                    analysis['risk_level'] = 'low'
                    analysis['recommendations'].append("Excellent vehicle history")
                elif score >= 80:
                    analysis['score_interpretation'] = 'good'
                    analysis['risk_level'] = 'low'
                    analysis['recommendations'].append("Good vehicle with minor issues")
                elif score >= 70:
                    analysis['score_interpretation'] = 'fair'
                    analysis['risk_level'] = 'medium'
                    analysis['recommendations'].append("Review detailed history carefully")
                elif score >= 60:
                    analysis['score_interpretation'] = 'below_average'
                    analysis['risk_level'] = 'medium'
                    analysis['recommendations'].append("Significant concerns present")
                else:
                    analysis['score_interpretation'] = 'poor'
                    analysis['risk_level'] = 'high'
                    analysis['recommendations'].append("High risk - avoid unless price reflects issues")
            
            # Additional analysis based on other factors
            accident_records = summary.get('accident_damage_records', '0')
            if accident_records != '0' and 'No' not in accident_records:
                analysis['recommendations'].append("Vehicle has accident/damage history")
            
            title_info = summary.get('title_info', '').lower()
            if any(issue in title_info for issue in ['lemon', 'flood', 'salvage']):
                analysis['risk_level'] = 'high'
                analysis['recommendations'].append(f"Title issue detected: {title_info}")
            
        except Exception as e:
            logger.error(f"AutoCheck analysis failed: {e}")
        
        return analysis
    
    def close(self):
        """Close browser if open"""
        if self.browser:
            self.browser.quit()
