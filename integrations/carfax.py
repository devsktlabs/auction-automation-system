
import requests
import time
import random
import re
import json
from typing import Dict, Optional, List, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from automation.browser import StealthBrowser
from utils.config import config
from utils.logger import logger
from utils.rate_limiter import rate_limiter, RateLimitConfig
from utils.errors import IntegrationError


class CarfaxServiceHistory:
    """
    Python implementation of CARFAX Service History API wrapper
    Based on the amattu2/CARFAX-Wrapper PHP implementation
    """
    
    # CARFAX Service History API endpoint
    _endpoint = "https://servicesocket.carfax.com/data/1"
    _product_data_id = None
    _location_id = None
    
    @classmethod
    def set_location_id(cls, location_id: str) -> None:
        """
        Set the CARFAX Location ID (provided during account setup)
        
        Args:
            location_id: CARFAX Location ID string
        """
        if not location_id or not isinstance(location_id, str):
            raise ValueError("Location ID must be a non-empty string")
        if len(location_id) < 1 or len(location_id) > 50:
            raise ValueError("Location ID must be between 1 and 50 characters")
        cls._location_id = location_id
    
    @classmethod
    def set_product_data_id(cls, product_data_id: str) -> None:
        """
        Set the CARFAX Product Data ID (API key equivalent)
        
        Args:
            product_data_id: CARFAX Product Data ID string
        """
        if not product_data_id or not isinstance(product_data_id, str):
            raise ValueError("Product Data ID must be a non-empty string")
        if len(product_data_id) != 16:
            raise ValueError("Product Data ID must be exactly 16 characters")
        cls._product_data_id = product_data_id
    
    @classmethod
    def get(cls, vin: str) -> Dict[str, Union[str, int, List, Dict]]:
        """
        Fetch vehicle history by VIN
        
        Args:
            vin: 17-character Vehicle Identification Number
            
        Returns:
            Dictionary containing vehicle decode, overview, and records
            
        Raises:
            ValueError: If VIN format is invalid
            RuntimeError: If Location ID or Product Data ID not set
        """
        # Validate VIN format
        if not vin or not isinstance(vin, str):
            raise ValueError("VIN must be a non-empty string")
        
        vin = vin.upper().strip()
        if not re.match(r'^[A-Z0-9]{17}$', vin):
            raise ValueError("VIN must be exactly 17 alphanumeric characters")
        
        # Validate required credentials
        if not cls._product_data_id:
            raise RuntimeError("Product Data ID must be set before making requests")
        if not cls._location_id:
            raise RuntimeError("Location ID must be set before making requests")
        
        # Make API request
        response_data = cls._post({
            'productDataId': cls._product_data_id,
            'locationId': cls._location_id,
            'vin': vin
        })
        
        if not response_data:
            # Return empty formatted result if API fails
            return {
                'Decode': {
                    'VIN': vin,
                    'Year': '',
                    'Make': '',
                    'Model': '',
                    'Trim': '',
                    'Driveline': ''
                },
                'Overview': [],
                'Records': []
            }
        
        # Format and return the response
        return cls._format_response(response_data, vin)
    
    @classmethod
    def _post(cls, fields: Dict[str, str]) -> Optional[Dict]:
        """
        Submit POST request to CARFAX Service History API
        
        Args:
            fields: Dictionary containing API request parameters
            
        Returns:
            Parsed response data or None if request fails
        """
        try:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'CARFAX-Python-Wrapper/1.0'
            }
            
            response = requests.post(
                cls._endpoint,
                json=fields,
                headers=headers,
                timeout=10
            )
            
            # Check for HTTP errors
            if response.status_code != 200:
                logger.warning(f"CARFAX API returned status {response.status_code}")
                return None
            
            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.error("Failed to parse CARFAX API response as JSON")
                return None
            
            # Check for API error messages
            if 'errorMessages' in data and data['errorMessages']:
                logger.error(f"CARFAX API error: {data['errorMessages']}")
                return None
            
            # Validate service history data
            if 'serviceHistory' not in data or not isinstance(data['serviceHistory'], list):
                logger.warning("CARFAX API response missing or invalid serviceHistory")
                return None
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"CARFAX API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in CARFAX API request: {e}")
            return None
    
    @classmethod
    def _format_response(cls, data: Dict, vin: str) -> Dict[str, Union[str, int, List, Dict]]:
        """
        Format API response to match expected structure
        
        Args:
            data: Raw API response data
            vin: Original VIN for the request
            
        Returns:
            Formatted response dictionary
        """
        result = {
            'Decode': {
                'VIN': vin,
                'Year': '',
                'Make': '',
                'Model': '',
                'Trim': '',
                'Driveline': ''
            },
            'Overview': [],
            'Records': []
        }
        
        try:
            service_history = data.get('serviceHistory', [])
            
            # Extract vehicle decode information from first record if available
            if service_history:
                first_record = service_history[0]
                result['Decode'].update({
                    'Year': str(first_record.get('year', '')),
                    'Make': first_record.get('make', ''),
                    'Model': first_record.get('model', ''),
                    'Trim': first_record.get('bodyTypeDescription', ''),
                    'Driveline': first_record.get('driveline', '')
                })
            
            # Process service categories for overview
            service_categories = {}
            
            # Process detailed records
            for record in service_history:
                # Extract record details
                record_date = cls._parse_date(record.get('date'))
                odometer = cls._parse_odometer(record.get('odometer'))
                services = record.get('services', [])
                record_type = record.get('type', 'Service')
                
                # Add to detailed records
                result['Records'].append({
                    'Date': record_date,
                    'Odometer': odometer,
                    'Services': services if isinstance(services, list) else [str(services)],
                    'Type': record_type
                })
                
                # Update service categories for overview
                for service in services:
                    if isinstance(service, str):
                        service_name = service.strip()
                        if service_name:
                            if service_name not in service_categories:
                                service_categories[service_name] = {
                                    'Name': service_name,
                                    'Date': record_date,
                                    'Odometer': odometer
                                }
                            else:
                                # Update with most recent occurrence
                                if record_date and (not service_categories[service_name]['Date'] or 
                                                  record_date > service_categories[service_name]['Date']):
                                    service_categories[service_name]['Date'] = record_date
                                    service_categories[service_name]['Odometer'] = odometer
            
            # Convert service categories to overview list
            result['Overview'] = list(service_categories.values())
            
        except Exception as e:
            logger.error(f"Error formatting CARFAX response: {e}")
        
        return result
    
    @classmethod
    def _parse_date(cls, date_value) -> Optional[str]:
        """Parse date value, returning None for invalid dates"""
        if not date_value or date_value == "Not Reported":
            return None
        return str(date_value) if date_value else None
    
    @classmethod
    def _parse_odometer(cls, odometer_value) -> int:
        """Parse odometer value, returning 0 for invalid values"""
        if not odometer_value:
            return 0
        try:
            return int(odometer_value)
        except (ValueError, TypeError):
            return 0


class CarfaxIntegrator:
    """
    Enhanced Carfax vehicle history integration using CARFAX-Wrapper approach
    with API and scraping fallback
    """
    
    def __init__(self):
        carfax_config = config.get_integration_config('carfax')
        
        # CARFAX API credentials (following wrapper pattern)
        self.product_data_id = carfax_config.get('product_data_id')
        self.location_id = carfax_config.get('location_id')
        
        # Legacy API key support
        self.api_key = carfax_config.get('api_key')
        
        # Configuration options
        self.fallback_scraping = carfax_config.get('fallback_scraping', True)
        self.use_wrapper_api = carfax_config.get('use_wrapper_api', True)
        
        # Initialize session for legacy API calls
        self.session = requests.Session()
        self.browser = None
        self.rate_config = RateLimitConfig(
            requests_per_minute=10,
            burst_limit=3,
            cooldown_seconds=6
        )
        
        # Configure CARFAX Service History wrapper if credentials available
        if self.product_data_id and self.location_id:
            try:
                CarfaxServiceHistory.set_product_data_id(self.product_data_id)
                CarfaxServiceHistory.set_location_id(self.location_id)
                logger.info("CARFAX Service History wrapper configured successfully")
            except Exception as e:
                logger.warning(f"Failed to configure CARFAX wrapper: {e}")
                self.use_wrapper_api = False
        else:
            logger.info("CARFAX wrapper credentials not available, using fallback methods")
            self.use_wrapper_api = False
        
        # Configure legacy API session
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def get_vehicle_history(self, vin: str) -> Dict[str, any]:
        """Get comprehensive vehicle history report"""
        try:
            # Try CARFAX wrapper API first if configured
            if self.use_wrapper_api:
                wrapper_result = self._get_history_wrapper(vin)
                if wrapper_result and wrapper_result.get('Records'):
                    return wrapper_result
            
            # Try legacy API if available
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
    
    def _get_history_wrapper(self, vin: str) -> Optional[Dict[str, any]]:
        """Get history using CARFAX Service History wrapper"""
        try:
            logger.info(f"Fetching CARFAX history for VIN {vin} using wrapper API")
            
            # Use the wrapper to get service history
            history_data = CarfaxServiceHistory.get(vin)
            
            if history_data and (history_data.get('Records') or history_data.get('Overview')):
                # Add metadata
                history_data['vin'] = vin
                history_data['source'] = 'carfax_wrapper_api'
                history_data['timestamp'] = time.time()
                
                logger.info(f"Successfully retrieved CARFAX data for VIN {vin}")
                return history_data
            else:
                logger.warning(f"No CARFAX data found for VIN {vin}")
                return None
                
        except Exception as e:
            logger.error(f"CARFAX wrapper API request failed for {vin}: {e}")
            return None
    
    def _get_history_api(self, vin: str) -> Optional[Dict[str, any]]:
        """Get history using legacy Carfax API"""
        try:
            url = f"https://api.carfax.com/v1/vehicle/{vin}/history"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                data['source'] = 'carfax_legacy_api'
                return data
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
            # Handle different data sources
            if history_data.get('source') == 'carfax_wrapper_api':
                flags = self._analyze_wrapper_data(history_data, flags)
            else:
                # Legacy analysis for scraping/other sources
                summary = history_data.get('summary', {})
                flags = self._analyze_summary_data(summary, flags)
            
        except Exception as e:
            logger.error(f"History analysis failed: {e}")
        
        return flags
    
    def _analyze_wrapper_data(self, history_data: Dict[str, any], flags: Dict[str, any]) -> Dict[str, any]:
        """Analyze data from CARFAX wrapper API"""
        try:
            records = history_data.get('Records', [])
            overview = history_data.get('Overview', [])
            
            # Count different types of records
            accident_count = 0
            service_count = len(overview)
            recall_count = 0
            
            for record in records:
                record_type = record.get('Type', '').lower()
                services = record.get('Services', [])
                
                if record_type == 'recall':
                    recall_count += 1
                
                # Check for accident indicators in services
                for service in services:
                    if isinstance(service, str):
                        service_lower = service.lower()
                        if any(keyword in service_lower for keyword in ['accident', 'collision', 'damage', 'repair']):
                            accident_count += 1
                            break
            
            # Red flags
            if accident_count > 2:
                flags['red_flags'].append(f"Multiple accident/damage records ({accident_count})")
            
            if recall_count > 3:
                flags['red_flags'].append(f"Multiple recalls ({recall_count})")
            
            # Check for title issues in services
            for record in records:
                services = record.get('Services', [])
                for service in services:
                    if isinstance(service, str):
                        service_lower = service.lower()
                        if any(keyword in service_lower for keyword in ['flood', 'lemon', 'salvage', 'total loss']):
                            flags['red_flags'].append(f"Title issue: {service}")
            
            # Yellow flags
            if accident_count == 1:
                flags['yellow_flags'].append("One accident/damage record found")
            
            if service_count < 3:
                flags['yellow_flags'].append("Limited service history")
            
            if recall_count > 0:
                flags['yellow_flags'].append(f"Vehicle has {recall_count} recall(s)")
            
            # Green flags
            if accident_count == 0:
                flags['green_flags'].append("No accident records found")
            
            if service_count > 10:
                flags['green_flags'].append("Extensive service history")
            
            if service_count >= 5:
                flags['green_flags'].append("Good maintenance record")
            
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
            else:
                flags['overall_risk'] = 'unknown'
            
        except Exception as e:
            logger.error(f"Wrapper data analysis failed: {e}")
        
        return flags
    
    def _analyze_summary_data(self, summary: Dict[str, any], flags: Dict[str, any]) -> Dict[str, any]:
        """Analyze legacy summary data"""
        try:
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
            logger.error(f"Summary data analysis failed: {e}")
        
        return flags
    
    def close(self):
        """Close browser if open"""
        if self.browser:
            self.browser.quit()
