
import requests
import time
import random
from typing import Dict, Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from automation.browser import StealthBrowser
from utils.config import config
from utils.logger import logger
from utils.rate_limiter import rate_limiter, RateLimitConfig
from utils.errors import IntegrationError

class CarfaxIntegrator:
    """Carfax vehicle history integration with API and scraping fallback"""
    
    def __init__(self):
        self.api_key = config.get_integration_config('carfax').get('api_key')
        self.fallback_scraping = config.get_integration_config('carfax').get('fallback_scraping', True)
        self.session = requests.Session()
        self.browser = None
        self.rate_config = RateLimitConfig(
            requests_per_minute=10,
            burst_limit=3,
            cooldown_seconds=6
        )
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def get_vehicle_history(self, vin: str) -> Dict[str, any]:
        """Get comprehensive vehicle history report"""
        try:
            # Try API first if available
            if self.api_key:
                api_result = self._get_history_api(vin)
                if api_result:
                    return api_result
            
            # Fallback to scraping if enabled
            if self.fallback_scraping:
                return self._get_history_scraping(vin)
            
            return {}
            
        except Exception as e:
            logger.error(f"Carfax history lookup failed for {vin}: {e}")
            return {}
    
    def _get_history_api(self, vin: str) -> Optional[Dict[str, any]]:
        """Get history using official Carfax API"""
        try:
            url = f"https://api.carfax.com/v1/vehicle/{vin}/history"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("Carfax API rate limit exceeded")
                return None
            else:
                logger.warning(f"Carfax API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Carfax API request failed: {e}")
            return None
    
    def _get_history_scraping(self, vin: str) -> Dict[str, any]:
        """Get history using web scraping"""
        try:
            # Rate limiting
            rate_limiter.wait_if_needed('carfax', self.rate_config)
            
            if not self.browser:
                self.browser = StealthBrowser("carfax")
                self.driver = self.browser.create_stealth_driver()
            
            # Navigate to Carfax VIN lookup
            url = f"https://www.carfax.com/vehicle/{vin}"
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(random.uniform(3, 6))
            
            # Extract summary data
            summary = self._extract_carfax_summary()
            
            # Record request for rate limiting
            rate_limiter.record_request('carfax')
            
            return {
                'vin': vin,
                'source': 'carfax_scraping',
                'summary': summary,
                'report_url': url
            }
            
        except Exception as e:
            logger.error(f"Carfax scraping failed for {vin}: {e}")
            return {}
    
    def _extract_carfax_summary(self) -> Dict[str, any]:
        """Extract key information from Carfax page"""
        summary = {}
        
        try:
            # Accident count
            try:
                accident_element = self.driver.find_element(
                    By.XPATH, 
                    "//span[contains(text(), 'accident')]/preceding-sibling::span"
                )
                summary['accident_count'] = int(accident_element.text.strip())
            except (NoSuchElementException, ValueError):
                summary['accident_count'] = 0
            
            # Service records
            try:
                service_element = self.driver.find_element(
                    By.XPATH,
                    "//span[contains(text(), 'service')]/preceding-sibling::span"
                )
                summary['service_records'] = int(service_element.text.strip())
            except (NoSuchElementException, ValueError):
                summary['service_records'] = 0
            
            # Previous owners
            try:
                owner_element = self.driver.find_element(
                    By.XPATH,
                    "//span[contains(text(), 'owner')]/preceding-sibling::span"
                )
                summary['previous_owners'] = int(owner_element.text.strip())
            except (NoSuchElementException, ValueError):
                summary['previous_owners'] = 0
            
            # Title issues
            title_issues = []
            try:
                issue_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".title-issue"
                )
                for element in issue_elements:
                    issue_text = element.text.strip()
                    if issue_text:
                        title_issues.append(issue_text)
            except NoSuchElementException:
                pass
            
            summary['title_issues'] = title_issues
            
            # Overall score/rating
            try:
                score_element = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".carfax-score"
                )
                summary['carfax_score'] = score_element.text.strip()
            except NoSuchElementException:
                summary['carfax_score'] = None
            
        except Exception as e:
            logger.error(f"Carfax summary extraction failed: {e}")
        
        return summary
    
    def analyze_history_flags(self, history_data: Dict[str, any]) -> Dict[str, any]:
        """Analyze history data for red flags"""
        flags = {
            'red_flags': [],
            'yellow_flags': [],
            'green_flags': [],
            'overall_risk': 'unknown'
        }
        
        try:
            summary = history_data.get('summary', {})
            
            # Red flags
            if summary.get('accident_count', 0) > 2:
                flags['red_flags'].append(f"Multiple accidents ({summary['accident_count']})")
            
            if summary.get('title_issues'):
                for issue in summary['title_issues']:
                    if any(keyword in issue.lower() for keyword in ['flood', 'lemon', 'salvage']):
                        flags['red_flags'].append(f"Title issue: {issue}")
            
            if summary.get('previous_owners', 0) > 4:
                flags['red_flags'].append(f"Many previous owners ({summary['previous_owners']})")
            
            # Yellow flags
            if summary.get('accident_count', 0) == 1:
                flags['yellow_flags'].append("One reported accident")
            
            if summary.get('service_records', 0) < 5:
                flags['yellow_flags'].append("Limited service history")
            
            # Green flags
            if summary.get('accident_count', 0) == 0:
                flags['green_flags'].append("No reported accidents")
            
            if summary.get('service_records', 0) > 10:
                flags['green_flags'].append("Well-maintained service history")
            
            if summary.get('previous_owners', 0) <= 2:
                flags['green_flags'].append("Few previous owners")
            
            # Overall risk assessment
            red_count = len(flags['red_flags'])
            yellow_count = len(flags['yellow_flags'])
            green_count = len(flags['green_flags'])
            
            if red_count > 0:
                flags['overall_risk'] = 'high'
            elif yellow_count > green_count:
                flags['overall_risk'] = 'medium'
            elif green_count > 0:
                flags['overall_risk'] = 'low'
            
        except Exception as e:
            logger.error(f"History analysis failed: {e}")
        
        return flags
    
    def close(self):
        """Close browser if open"""
        if self.browser:
            self.browser.quit()
