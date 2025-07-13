
import time
import random
import re
from typing import List, Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dataclasses import dataclass
import requests

from automation.browser import StealthBrowser
from utils.config import config
from utils.logger import logger
from utils.rate_limiter import rate_limiter, RateLimitConfig
from utils.errors import ScrapingError, AuthenticationError, IntegrationError

@dataclass
class ManheimVehicle:
    vin: str
    year: int
    make: str
    model: str
    trim: str
    mileage: int
    mmr_value: Optional[float]
    current_bid: float
    reserve_price: Optional[float]
    time_left: str
    condition_report: Dict[str, any]
    location: str
    images: List[str]
    manheim_url: str

class ManheimScraper:
    """Advanced Manheim auction scraper with API integration"""
    
    def __init__(self, profile_name: str = "manheim"):
        self.browser = StealthBrowser(profile_name)
        self.driver = None
        self.base_url = config.get_platform_config('manheim')['base_url']
        self.api_base = config.get_platform_config('manheim')['api_base']
        self.api_key = config.get_integration_config('manheim').get('api_key')
        self.rate_config = RateLimitConfig(
            requests_per_minute=config.get_platform_config('manheim')['rate_limit'],
            burst_limit=2,
            cooldown_seconds=15
        )
        self.session = requests.Session()
        self._setup_api_session()
        
    def _setup_api_session(self):
        """Setup API session with authentication"""
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'AuctionBot/1.0'
            })
    
    def initialize(self):
        """Initialize browser and login if needed"""
        try:
            self.driver = self.browser.create_stealth_driver()
            
            # Try to load existing session
            if not self.browser.load_session_cookies('manheim'):
                logger.info("No valid Manheim session found, manual login required")
                return False
            
            # Verify session is still valid
            self.driver.get(self.base_url)
            time.sleep(3)
            
            if self._is_logged_in():
                logger.info("Successfully restored Manheim session")
                return True
            else:
                logger.info("Manheim session expired, manual login required")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize Manheim scraper: {e}")
            raise ScrapingError(f"Initialization failed: {e}")
    
    def login(self, username: str, password: str) -> bool:
        """Login to Manheim auction platform"""
        try:
            logger.info("Attempting Manheim login")
            
            # Navigate to login page
            login_url = f"{self.base_url}/login"
            self.driver.get(login_url)
            self.browser.human_like_delay(2, 4)
            
            # Find and fill username
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            self.browser.human_mouse_movement(username_field)
            username_field.clear()
            self._type_like_human(username_field, username)
            
            # Find and fill password
            password_field = self.driver.find_element(By.NAME, "password")
            self.browser.human_mouse_movement(password_field)
            password_field.clear()
            self._type_like_human(password_field, password)
            
            # Submit login form
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.browser.human_mouse_movement(login_button)
            login_button.click()
            
            # Wait for login completion
            WebDriverWait(self.driver, 15).until(
                lambda driver: self._is_logged_in()
            )
            
            # Save session
            self.browser.save_session_cookies('manheim')
            
            logger.info("Manheim login successful")
            return True
            
        except Exception as e:
            logger.error(f"Manheim login failed: {e}")
            raise AuthenticationError(f"Login failed: {e}")
    
    def _is_logged_in(self) -> bool:
        """Check if user is logged in"""
        try:
            # Look for auction dashboard or user menu
            dashboard_indicators = [
                "//div[contains(@class, 'auction-dashboard')]",
                "//a[contains(@href, 'logout')]",
                "//div[contains(@class, 'user-profile')]"
            ]
            
            for indicator in dashboard_indicators:
                try:
                    self.driver.find_element(By.XPATH, indicator)
                    return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _type_like_human(self, element, text: str):
        """Type text with human-like timing"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
    
    def get_mmr_valuations_api(self, vins: List[str]) -> Dict[str, Dict]:
        """Get MMR valuations using official API"""
        if not self.api_key:
            logger.warning("No Manheim API key configured, skipping API valuations")
            return {}
        
        try:
            endpoint = f"{self.api_base}/valuations/batch"
            payload = {'vins': vins}
            
            response = self.session.post(endpoint, json=payload)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("API rate limit exceeded")
                return {}
            else:
                logger.error(f"API request failed: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"MMR API request failed: {e}")
            return {}
    
    def search_vehicles(self, criteria: Dict[str, any]) -> List[str]:
        """Search for vehicles matching criteria"""
        try:
            logger.info(f"Searching Manheim vehicles with criteria: {criteria}")
            
            # Try API search first
            if self.api_key:
                api_results = self._search_vehicles_api(criteria)
                if api_results:
                    return api_results
            
            # Fallback to web scraping
            return self._search_vehicles_web(criteria)
            
        except Exception as e:
            logger.error(f"Vehicle search failed: {e}")
            raise ScrapingError(f"Search failed: {e}")
    
    def _search_vehicles_api(self, criteria: Dict[str, any]) -> List[str]:
        """Search vehicles using API"""
        try:
            endpoint = f"{self.api_base}/inventory/search"
            
            # Convert criteria to API format
            api_criteria = {
                'year_min': criteria.get('year_min'),
                'year_max': criteria.get('year_max'),
                'make': criteria.get('make'),
                'model': criteria.get('model'),
                'mileage_max': criteria.get('mileage_max'),
                'price_max': criteria.get('price_max'),
                'location_radius': criteria.get('location_radius', 500)
            }
            
            # Remove None values
            api_criteria = {k: v for k, v in api_criteria.items() if v is not None}
            
            response = self.session.post(endpoint, json=api_criteria)
            
            if response.status_code == 200:
                results = response.json()
                return [vehicle['url'] for vehicle in results.get('vehicles', [])]
            
            return []
            
        except Exception as e:
            logger.error(f"API search failed: {e}")
            return []
    
    def _search_vehicles_web(self, criteria: Dict[str, any]) -> List[str]:
        """Search vehicles using web scraping"""
        try:
            # Navigate to search page
            search_url = f"{self.base_url}/search"
            self.driver.get(search_url)
            self.browser.human_like_delay(2, 4)
            
            # Apply search filters
            self._apply_search_filters(criteria)
            
            # Get vehicle URLs from search results
            vehicle_urls = self._extract_vehicle_urls()
            
            logger.info(f"Found {len(vehicle_urls)} vehicles via web scraping")
            return vehicle_urls
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    def _apply_search_filters(self, criteria: Dict[str, any]):
        """Apply search filters on web interface"""
        try:
            # Year range
            if 'year_min' in criteria:
                year_min_field = self.driver.find_element(By.NAME, "yearMin")
                year_min_field.clear()
                year_min_field.send_keys(str(criteria['year_min']))
            
            if 'year_max' in criteria:
                year_max_field = self.driver.find_element(By.NAME, "yearMax")
                year_max_field.clear()
                year_max_field.send_keys(str(criteria['year_max']))
            
            # Make selection
            if 'make' in criteria:
                make_dropdown = self.driver.find_element(By.NAME, "make")
                make_dropdown.send_keys(criteria['make'])
            
            # Model selection
            if 'model' in criteria:
                model_dropdown = self.driver.find_element(By.NAME, "model")
                model_dropdown.send_keys(criteria['model'])
            
            # Mileage
            if 'mileage_max' in criteria:
                mileage_field = self.driver.find_element(By.NAME, "mileageMax")
                mileage_field.clear()
                mileage_field.send_keys(str(criteria['mileage_max']))
            
            # Submit search
            search_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.browser.human_mouse_movement(search_button)
            search_button.click()
            
            # Wait for results
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "vehicle-listing"))
            )
            
        except Exception as e:
            logger.error(f"Failed to apply search filters: {e}")
    
    def _extract_vehicle_urls(self) -> List[str]:
        """Extract vehicle URLs from search results"""
        vehicle_urls = []
        
        try:
            # Find all vehicle listing links
            vehicle_links = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "a[href*='/vehicle/']"
            )
            
            for link in vehicle_links:
                href = link.get_attribute('href')
                if href and '/vehicle/' in href:
                    vehicle_urls.append(href)
            
            # Handle pagination
            vehicle_urls.extend(self._handle_pagination())
            
        except Exception as e:
            logger.error(f"Failed to extract vehicle URLs: {e}")
        
        return list(set(vehicle_urls))
    
    def _handle_pagination(self) -> List[str]:
        """Handle pagination to get all results"""
        all_urls = []
        
        try:
            while True:
                try:
                    next_button = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        "a[aria-label='Next page']"
                    )
                    
                    if not next_button.is_enabled():
                        break
                    
                    self.browser.human_mouse_movement(next_button)
                    next_button.click()
                    self.browser.human_like_delay(3, 5)
                    
                    page_urls = self._extract_vehicle_urls_current_page()
                    all_urls.extend(page_urls)
                    
                except NoSuchElementException:
                    break
                    
        except Exception as e:
            logger.error(f"Pagination handling failed: {e}")
        
        return all_urls
    
    def _extract_vehicle_urls_current_page(self) -> List[str]:
        """Extract URLs from current page only"""
        urls = []
        
        try:
            vehicle_links = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "a[href*='/vehicle/']"
            )
            
            for link in vehicle_links:
                href = link.get_attribute('href')
                if href and '/vehicle/' in href:
                    urls.append(href)
                    
        except Exception as e:
            logger.error(f"Failed to extract URLs from current page: {e}")
        
        return urls
    
    def scrape_vehicle_details(self, vehicle_url: str) -> Optional[ManheimVehicle]:
        """Scrape detailed information for a specific vehicle"""
        try:
            # Rate limiting
            rate_limiter.wait_if_needed('manheim', self.rate_config)
            
            logger.info(f"Scraping Manheim vehicle: {vehicle_url}")
            
            # Navigate to vehicle page
            self.driver.get(vehicle_url)
            self.browser.human_like_delay(3, 5)
            
            # Extract vehicle data
            vehicle_data = self._extract_vehicle_data()
            vehicle_data['manheim_url'] = vehicle_url
            
            # Get MMR value if VIN available
            if vehicle_data.get('vin'):
                mmr_data = self.get_mmr_valuations_api([vehicle_data['vin']])
                if mmr_data and vehicle_data['vin'] in mmr_data:
                    vehicle_data['mmr_value'] = mmr_data[vehicle_data['vin']].get('value')
            
            # Record request for rate limiting
            rate_limiter.record_request('manheim')
            
            return ManheimVehicle(**vehicle_data)
            
        except Exception as e:
            logger.error(f"Failed to scrape Manheim vehicle {vehicle_url}: {e}")
            return None
    
    def _extract_vehicle_data(self) -> Dict[str, any]:
        """Extract all vehicle data from current page"""
        data = {}
        
        try:
            # VIN
            data['vin'] = self._extract_vin()
            
            # Basic vehicle info
            title = self._extract_title()
            data.update(self._parse_vehicle_title(title))
            
            # Mileage
            data['mileage'] = self._extract_mileage()
            
            # Pricing
            data['current_bid'] = self._extract_current_bid()
            data['reserve_price'] = self._extract_reserve_price()
            data['mmr_value'] = None  # Will be filled by API call
            
            # Auction info
            data['time_left'] = self._extract_time_left()
            data['location'] = self._extract_location()
            
            # Condition report
            data['condition_report'] = self._extract_condition_report()
            
            # Images
            data['images'] = self._extract_images()
            
        except Exception as e:
            logger.error(f"Manheim data extraction failed: {e}")
            raise ScrapingError(f"Vehicle data extraction failed: {e}")
        
        return data
    
    def _extract_vin(self) -> str:
        """Extract VIN from vehicle page"""
        try:
            vin_selectors = [
                "[data-vin]",
                ".vin-number",
                "//span[contains(text(), 'VIN:')]/following-sibling::span",
                "//dt[contains(text(), 'VIN')]/following-sibling::dd"
            ]
            
            for selector in vin_selectors:
                try:
                    if selector.startswith("//"):
                        element = self.driver.find_element(By.XPATH, selector)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    vin = element.get_attribute('data-vin') or element.text.strip()
                    if vin and len(vin) == 17:
                        return vin
                        
                except NoSuchElementException:
                    continue
            
            return ""
            
        except Exception as e:
            logger.error(f"VIN extraction failed: {e}")
            return ""
    
    def _extract_title(self) -> str:
        """Extract vehicle title"""
        try:
            title_element = self.driver.find_element(By.CSS_SELECTOR, "h1.vehicle-title")
            return title_element.text.strip()
        except NoSuchElementException:
            return ""
    
    def _parse_vehicle_title(self, title: str) -> Dict[str, any]:
        """Parse year, make, model, trim from title"""
        parts = title.split()
        
        if len(parts) >= 3:
            return {
                'year': int(parts[0]) if parts[0].isdigit() else 0,
                'make': parts[1],
                'model': parts[2],
                'trim': ' '.join(parts[3:]) if len(parts) > 3 else ''
            }
        
        return {'year': 0, 'make': '', 'model': '', 'trim': ''}
    
    def _extract_mileage(self) -> int:
        """Extract vehicle mileage"""
        try:
            mileage_element = self.driver.find_element(By.CSS_SELECTOR, ".vehicle-mileage")
            mileage_text = mileage_element.text.strip()
            # Extract numbers only
            mileage_str = re.sub(r'[^\d]', '', mileage_text)
            return int(mileage_str) if mileage_str else 0
        except (NoSuchElementException, ValueError):
            return 0
    
    def _extract_current_bid(self) -> float:
        """Extract current bid amount"""
        try:
            bid_element = self.driver.find_element(By.CSS_SELECTOR, ".current-bid")
            bid_text = bid_element.text.strip()
            return self._parse_currency(bid_text)
        except NoSuchElementException:
            return 0.0
    
    def _extract_reserve_price(self) -> Optional[float]:
        """Extract reserve price if available"""
        try:
            reserve_element = self.driver.find_element(By.CSS_SELECTOR, ".reserve-price")
            reserve_text = reserve_element.text.strip()
            return self._parse_currency(reserve_text)
        except NoSuchElementException:
            return None
    
    def _parse_currency(self, text: str) -> float:
        """Parse currency string to float"""
        cleaned = re.sub(r'[^\d.]', '', text)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _extract_time_left(self) -> str:
        """Extract auction time remaining"""
        try:
            time_element = self.driver.find_element(By.CSS_SELECTOR, ".time-left")
            return time_element.text.strip()
        except NoSuchElementException:
            return ""
    
    def _extract_location(self) -> str:
        """Extract vehicle location"""
        try:
            location_element = self.driver.find_element(By.CSS_SELECTOR, ".vehicle-location")
            return location_element.text.strip()
        except NoSuchElementException:
            return ""
    
    def _extract_condition_report(self) -> Dict[str, any]:
        """Extract condition report data"""
        condition_data = {}
        
        try:
            # Look for condition report section
            condition_section = self.driver.find_element(By.CSS_SELECTOR, ".condition-report")
            
            # Extract overall grade
            try:
                grade_element = condition_section.find_element(By.CSS_SELECTOR, ".overall-grade")
                condition_data['overall_grade'] = grade_element.text.strip()
            except NoSuchElementException:
                pass
            
            # Extract specific condition items
            condition_items = condition_section.find_elements(By.CSS_SELECTOR, ".condition-item")
            
            for item in condition_items:
                try:
                    category = item.find_element(By.CSS_SELECTOR, ".category").text.strip()
                    rating = item.find_element(By.CSS_SELECTOR, ".rating").text.strip()
                    condition_data[category.lower().replace(' ', '_')] = rating
                except NoSuchElementException:
                    continue
                    
        except NoSuchElementException:
            logger.debug("No condition report section found")
        except Exception as e:
            logger.error(f"Condition report extraction failed: {e}")
        
        return condition_data
    
    def _extract_images(self) -> List[str]:
        """Extract all vehicle images"""
        images = []
        
        try:
            image_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                ".vehicle-gallery img"
            )
            
            for img in image_elements:
                src = img.get_attribute('src')
                if src:
                    images.append(src)
                    
        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
        
        return images
    
    def close(self):
        """Close browser and cleanup"""
        if self.browser:
            self.browser.quit()
