
import time
import random
import re
from typing import List, Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dataclasses import dataclass

from automation.browser import StealthBrowser
from utils.config import config
from utils.logger import logger
from utils.rate_limiter import rate_limiter, RateLimitConfig
from utils.errors import ScrapingError, AuthenticationError

@dataclass
class CarMaxVehicle:
    vin: str
    year: int
    make: str
    model: str
    trim: str
    mileage: int
    current_bid: float
    buy_now_price: Optional[float]
    time_left: str
    condition_grade: str
    location: str
    images: List[str]
    obd2_codes: List[str]
    dashboard_lights: List[str]
    carmax_url: str

class CarMaxScraper:
    """Advanced CarMax auction scraper with stealth capabilities"""
    
    def __init__(self, profile_name: str = "carmax"):
        self.browser = StealthBrowser(profile_name)
        self.driver = None
        self.base_url = config.get_platform_config('carmax')['base_url']
        self.login_url = config.get_platform_config('carmax')['login_url']
        self.rate_config = RateLimitConfig(
            requests_per_minute=config.get_platform_config('carmax')['rate_limit'],
            burst_limit=3,
            cooldown_seconds=10
        )
        
    def initialize(self):
        """Initialize browser and login if needed"""
        try:
            self.driver = self.browser.create_stealth_driver()
            
            # Try to load existing session
            if not self.browser.load_session_cookies('carmax'):
                logger.info("No valid session found, manual login required")
                return False
            
            # Verify session is still valid
            self.driver.get(self.base_url)
            time.sleep(3)
            
            if self._is_logged_in():
                logger.info("Successfully restored CarMax session")
                return True
            else:
                logger.info("Session expired, manual login required")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize CarMax scraper: {e}")
            raise ScrapingError(f"Initialization failed: {e}")
    
    def login(self, username: str, password: str, mfa_secret: str = None) -> bool:
        """Login to CarMax auction platform"""
        try:
            logger.info("Attempting CarMax login")
            
            # Navigate to login page
            self.driver.get(self.login_url)
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
            
            # Handle MFA if required
            if mfa_secret and self._is_mfa_required():
                if not self._handle_mfa(mfa_secret):
                    raise AuthenticationError("MFA authentication failed")
            
            # Wait for login completion
            WebDriverWait(self.driver, 15).until(
                lambda driver: self._is_logged_in()
            )
            
            # Save session
            self.browser.save_session_cookies('carmax')
            
            logger.info("CarMax login successful")
            return True
            
        except Exception as e:
            logger.error(f"CarMax login failed: {e}")
            raise AuthenticationError(f"Login failed: {e}")
    
    def _is_logged_in(self) -> bool:
        """Check if user is logged in"""
        try:
            # Look for auction dashboard or user menu
            dashboard_indicators = [
                "//div[contains(@class, 'auction-dashboard')]",
                "//a[contains(@href, 'logout')]",
                "//div[contains(@class, 'user-menu')]"
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
    
    def _is_mfa_required(self) -> bool:
        """Check if MFA is required"""
        try:
            self.driver.find_element(By.ID, "mfa-code")
            return True
        except NoSuchElementException:
            return False
    
    def _handle_mfa(self, mfa_secret: str) -> bool:
        """Handle MFA authentication"""
        try:
            import pyotp
            
            totp = pyotp.TOTP(mfa_secret)
            code = totp.now()
            
            mfa_field = self.driver.find_element(By.ID, "mfa-code")
            self.browser.human_mouse_movement(mfa_field)
            mfa_field.clear()
            self._type_like_human(mfa_field, code)
            
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.browser.human_mouse_movement(submit_btn)
            submit_btn.click()
            
            return True
            
        except Exception as e:
            logger.error(f"MFA handling failed: {e}")
            return False
    
    def _type_like_human(self, element, text: str):
        """Type text with human-like timing"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
    
    def search_vehicles(self, criteria: Dict[str, any]) -> List[str]:
        """Search for vehicles matching criteria and return URLs"""
        try:
            logger.info(f"Searching CarMax vehicles with criteria: {criteria}")
            
            # Navigate to search page
            search_url = f"{self.base_url}/search"
            self.driver.get(search_url)
            self.browser.human_like_delay(2, 4)
            
            # Apply search filters
            self._apply_search_filters(criteria)
            
            # Get vehicle URLs from search results
            vehicle_urls = self._extract_vehicle_urls()
            
            logger.info(f"Found {len(vehicle_urls)} vehicles matching criteria")
            return vehicle_urls
            
        except Exception as e:
            logger.error(f"Vehicle search failed: {e}")
            raise ScrapingError(f"Search failed: {e}")
    
    def _apply_search_filters(self, criteria: Dict[str, any]):
        """Apply search filters based on criteria"""
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
            
            # Price range
            if 'price_min' in criteria:
                price_min_field = self.driver.find_element(By.NAME, "priceMin")
                price_min_field.clear()
                price_min_field.send_keys(str(criteria['price_min']))
            
            if 'price_max' in criteria:
                price_max_field = self.driver.find_element(By.NAME, "priceMax")
                price_max_field.clear()
                price_max_field.send_keys(str(criteria['price_max']))
            
            # Mileage range
            if 'mileage_max' in criteria:
                mileage_field = self.driver.find_element(By.NAME, "mileageMax")
                mileage_field.clear()
                mileage_field.send_keys(str(criteria['mileage_max']))
            
            # Submit search
            search_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            self.browser.human_mouse_movement(search_button)
            search_button.click()
            
            # Wait for results to load
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
        
        return list(set(vehicle_urls))  # Remove duplicates
    
    def _handle_pagination(self) -> List[str]:
        """Handle pagination to get all vehicle URLs"""
        all_urls = []
        
        try:
            while True:
                # Check for next page button
                try:
                    next_button = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        "a[aria-label='Next page']"
                    )
                    
                    if not next_button.is_enabled():
                        break
                    
                    # Click next page
                    self.browser.human_mouse_movement(next_button)
                    next_button.click()
                    
                    # Wait for page to load
                    self.browser.human_like_delay(3, 5)
                    
                    # Extract URLs from this page
                    page_urls = self._extract_vehicle_urls_current_page()
                    all_urls.extend(page_urls)
                    
                except NoSuchElementException:
                    break
                    
        except Exception as e:
            logger.error(f"Pagination handling failed: {e}")
        
        return all_urls
    
    def _extract_vehicle_urls_current_page(self) -> List[str]:
        """Extract vehicle URLs from current page only"""
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
    
    def scrape_vehicle_details(self, vehicle_url: str) -> Optional[CarMaxVehicle]:
        """Scrape detailed information for a specific vehicle"""
        try:
            # Rate limiting
            rate_limiter.wait_if_needed('carmax', self.rate_config)
            
            logger.info(f"Scraping vehicle details: {vehicle_url}")
            
            # Navigate to vehicle page
            self.driver.get(vehicle_url)
            self.browser.human_like_delay(3, 5)
            
            # Extract vehicle data
            vehicle_data = self._extract_vehicle_data()
            vehicle_data['carmax_url'] = vehicle_url
            
            # Record request for rate limiting
            rate_limiter.record_request('carmax')
            
            return CarMaxVehicle(**vehicle_data)
            
        except Exception as e:
            logger.error(f"Failed to scrape vehicle {vehicle_url}: {e}")
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
            
            # Pricing
            data['current_bid'] = self._extract_current_bid()
            data['buy_now_price'] = self._extract_buy_now_price()
            
            # Auction info
            data['time_left'] = self._extract_time_left()
            data['condition_grade'] = self._extract_condition_grade()
            data['location'] = self._extract_location()
            
            # Images
            data['images'] = self._extract_images()
            
            # Diagnostic data
            data['obd2_codes'] = self._extract_obd2_codes()
            data['dashboard_lights'] = self._extract_dashboard_lights()
            
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            raise ScrapingError(f"Vehicle data extraction failed: {e}")
        
        return data
    
    def _extract_vin(self) -> str:
        """Extract VIN from vehicle page"""
        try:
            # Try multiple selectors for VIN
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
            
            raise ScrapingError("VIN not found")
            
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
        # Example: "2020 Honda Accord EX-L"
        parts = title.split()
        
        if len(parts) >= 3:
            return {
                'year': int(parts[0]) if parts[0].isdigit() else 0,
                'make': parts[1],
                'model': parts[2],
                'trim': ' '.join(parts[3:]) if len(parts) > 3 else ''
            }
        
        return {'year': 0, 'make': '', 'model': '', 'trim': ''}
    
    def _extract_current_bid(self) -> float:
        """Extract current bid amount"""
        try:
            bid_element = self.driver.find_element(By.CSS_SELECTOR, ".current-bid")
            bid_text = bid_element.text.strip()
            return self._parse_currency(bid_text)
        except NoSuchElementException:
            return 0.0
    
    def _extract_buy_now_price(self) -> Optional[float]:
        """Extract buy now price if available"""
        try:
            price_element = self.driver.find_element(By.CSS_SELECTOR, ".buy-now-price")
            price_text = price_element.text.strip()
            return self._parse_currency(price_text)
        except NoSuchElementException:
            return None
    
    def _parse_currency(self, text: str) -> float:
        """Parse currency string to float"""
        # Remove currency symbols and commas
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
    
    def _extract_condition_grade(self) -> str:
        """Extract condition grade"""
        try:
            grade_element = self.driver.find_element(By.CSS_SELECTOR, ".condition-grade")
            return grade_element.text.strip()
        except NoSuchElementException:
            return ""
    
    def _extract_location(self) -> str:
        """Extract vehicle location"""
        try:
            location_element = self.driver.find_element(By.CSS_SELECTOR, ".vehicle-location")
            return location_element.text.strip()
        except NoSuchElementException:
            return ""
    
    def _extract_images(self) -> List[str]:
        """Extract all vehicle images"""
        images = []
        
        try:
            # Find image gallery
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
    
    def _extract_obd2_codes(self) -> List[str]:
        """Extract OBD2 diagnostic codes"""
        codes = []
        
        try:
            # Look for OBD2 section
            obd2_section = self.driver.find_element(By.CSS_SELECTOR, ".obd2-codes")
            code_elements = obd2_section.find_elements(By.CSS_SELECTOR, ".diagnostic-code")
            
            for code_elem in code_elements:
                code = code_elem.text.strip()
                if code:
                    codes.append(code)
                    
        except NoSuchElementException:
            logger.debug("No OBD2 codes section found")
        except Exception as e:
            logger.error(f"OBD2 code extraction failed: {e}")
        
        return codes
    
    def _extract_dashboard_lights(self) -> List[str]:
        """Extract dashboard warning lights"""
        lights = []
        
        try:
            # Look for dashboard lights section
            dashboard_section = self.driver.find_element(By.CSS_SELECTOR, ".dashboard-lights")
            light_elements = dashboard_section.find_elements(By.CSS_SELECTOR, ".warning-light")
            
            for light_elem in light_elements:
                light = light_elem.text.strip()
                if light:
                    lights.append(light)
                    
        except NoSuchElementException:
            logger.debug("No dashboard lights section found")
        except Exception as e:
            logger.error(f"Dashboard lights extraction failed: {e}")
        
        return lights
    
    def close(self):
        """Close browser and cleanup"""
        if self.browser:
            self.browser.quit()
