
import os
import pickle
import random
import time
import json
import re
from pathlib import Path
from typing import Dict, Optional, List, Union
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    WebDriverException,
    ElementClickInterceptedException
)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from automation.browser import StealthBrowser
from utils.config import config
from utils.logger import logger
from utils.rate_limiter import rate_limiter, RateLimitConfig
from utils.errors import IntegrationError, AuthenticationError


class CarfaxDealerPortalScraper:
    """
    CARFAX Dealer Portal Web Scraper
    Automates login and VIN lookup using existing dealer portal access
    """
    
    # CARFAX Dealer Portal URLs
    DEALER_LOGIN_URL = "https://www.carfaxonline.com/"
    DEALER_PORTAL_BASE = "https://www.carfaxonline.com"
    VIN_LOOKUP_PATH = "/cfx/displayHistoryReport.cfx"
    
    # DOM Selectors (based on common patterns for dealer portals)
    LOGIN_SELECTORS = {
        'username_field': ['input[name="username"]', 'input[name="email"]', 'input[type="email"]', '#username', '#email'],
        'password_field': ['input[name="password"]', 'input[type="password"]', '#password'],
        'login_button': ['input[type="submit"]', 'button[type="submit"]', 'button:contains("Sign In")', 'button:contains("Login")', '.login-btn'],
        'remember_me': ['input[name="remember"]', 'input[type="checkbox"]'],
        'error_message': ['.error', '.alert-danger', '.login-error', '[class*="error"]']
    }
    
    VIN_SELECTORS = {
        'vin_input': ['input[name="vin"]', 'input[placeholder*="VIN"]', '#vin', '.vin-input'],
        'search_button': ['input[value*="Search"]', 'button:contains("Search")', 'button:contains("Run Report")', '.search-btn'],
        'report_container': ['.report-container', '.vehicle-history', '.carfax-report', '#report-content']
    }
    
    REPORT_SELECTORS = {
        'vehicle_info': {
            'year': ['.vehicle-year', '[data-field="year"]', '.year'],
            'make': ['.vehicle-make', '[data-field="make"]', '.make'],
            'model': ['.vehicle-model', '[data-field="model"]', '.model'],
            'trim': ['.vehicle-trim', '[data-field="trim"]', '.trim']
        },
        'accident_count': ['.accident-count', '[data-accidents]', '.accidents', 'span:contains("accident")'],
        'service_records': ['.service-record', '.maintenance-record', '.service-item'],
        'ownership_history': ['.owner-history', '.previous-owners', '.ownership'],
        'title_issues': ['.title-issue', '.title-problem', '.lemon', '.flood'],
        'odometer_readings': ['.odometer', '.mileage-reading', '[data-odometer]']
    }
    
    def __init__(self):
        self.browser = None
        self.driver = None
        self.session_file = None
        self.is_logged_in = False
        
        # Get credentials from config
        carfax_config = config.get_integration_config('carfax')
        self.username = carfax_config.get('dealer_username') or os.getenv('CARFAX_DEALER_USERNAME')
        self.password = carfax_config.get('dealer_password') or os.getenv('CARFAX_DEALER_PASSWORD')
        
        if not self.username or not self.password:
            logger.warning("CARFAX dealer credentials not found. Web scraping will not be available.")
        
        # Rate limiting configuration
        self.rate_config = RateLimitConfig(
            requests_per_minute=8,  # Conservative rate limit
            burst_limit=2,
            cooldown_seconds=8
        )
        
        # Session management
        self.session_cache_dir = Path.home() / '.cache' / 'auction_automation' / 'carfax'
        self.session_cache_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.session_cache_dir / 'dealer_session.pkl'
        
    def _init_browser(self):
        """Initialize stealth browser if not already done"""
        if not self.browser:
            self.browser = StealthBrowser("carfax_dealer")
            self.driver = self.browser.create_stealth_driver()
            logger.info("Initialized CARFAX dealer portal browser")
    
    def _find_element_by_selectors(self, selectors: List[str], timeout: int = 10):
        """Try multiple selectors to find an element"""
        wait = WebDriverWait(self.driver, timeout)
        
        for selector in selectors:
            try:
                if selector.startswith('#') or selector.startswith('.') or selector.startswith('['):
                    # CSS selector
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    return element
                elif ':contains(' in selector:
                    # XPath for text content
                    text_content = selector.split(':contains("')[1].split('")')[0]
                    xpath = f"//*[contains(text(), '{text_content}')]"
                    element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    return element
                else:
                    # Try as CSS selector first, then as name
                    try:
                        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        return element
                    except:
                        element = wait.until(EC.presence_of_element_located((By.NAME, selector)))
                        return element
            except (TimeoutException, NoSuchElementException):
                continue
        
        raise NoSuchElementException(f"Could not find element with any of the selectors: {selectors}")
    
    def _save_session(self):
        """Save current session cookies"""
        if not self.driver:
            return
            
        try:
            session_data = {
                'cookies': self.driver.get_cookies(),
                'timestamp': datetime.now().isoformat(),
                'url': self.driver.current_url,
                'is_logged_in': self.is_logged_in
            }
            
            with open(self.session_file, 'wb') as f:
                pickle.dump(session_data, f)
            
            logger.info("Saved CARFAX dealer session")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def _load_session(self) -> bool:
        """Load saved session if valid"""
        if not self.session_file.exists():
            return False
            
        try:
            with open(self.session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            # Check if session is still valid (24 hours)
            timestamp = datetime.fromisoformat(session_data['timestamp'])
            if datetime.now() - timestamp > timedelta(hours=24):
                logger.info("CARFAX session expired")
                return False
            
            # Initialize browser and load cookies
            self._init_browser()
            self.driver.get(self.DEALER_LOGIN_URL)
            
            # Load cookies
            for cookie in session_data['cookies']:
                try:
                    # Remove problematic keys
                    cookie.pop('expiry', None)
                    cookie.pop('sameSite', None)
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Failed to add cookie: {e}")
            
            # Refresh page to apply cookies
            self.driver.refresh()
            time.sleep(3)
            
            # Check if still logged in
            if self._check_login_status():
                self.is_logged_in = True
                logger.info("Successfully restored CARFAX dealer session")
                return True
            else:
                logger.info("Saved session is no longer valid")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return False
    
    def _check_login_status(self) -> bool:
        """Check if currently logged into dealer portal"""
        try:
            # Look for indicators that we're logged in
            login_indicators = [
                'logout', 'sign out', 'dashboard', 'account', 'reports',
                'inventory', 'dealer portal', 'welcome'
            ]
            
            page_text = self.driver.page_source.lower()
            for indicator in login_indicators:
                if indicator in page_text:
                    return True
            
            # Check URL for dealer portal paths
            current_url = self.driver.current_url.lower()
            if any(path in current_url for path in ['dealer', 'portal', 'dashboard', 'account']):
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((TimeoutException, WebDriverException))
    )
    def login(self) -> bool:
        """Login to CARFAX dealer portal"""
        if not self.username or not self.password:
            raise AuthenticationError("CARFAX dealer credentials not configured")
        
        # Try to load existing session first
        if self._load_session():
            return True
        
        logger.info("Logging into CARFAX dealer portal")
        
        try:
            self._init_browser()
            
            # Navigate to login page
            self.driver.get(self.DEALER_LOGIN_URL)
            self.browser.human_like_delay(2, 4)
            
            # Find and fill username field
            username_field = self._find_element_by_selectors(self.LOGIN_SELECTORS['username_field'])
            username_field.clear()
            username_field.send_keys(self.username)
            self.browser.human_like_delay(1, 2)
            
            # Find and fill password field
            password_field = self._find_element_by_selectors(self.LOGIN_SELECTORS['password_field'])
            password_field.clear()
            password_field.send_keys(self.password)
            self.browser.human_like_delay(1, 2)
            
            # Try to check "Remember Me" if available
            try:
                remember_me = self._find_element_by_selectors(self.LOGIN_SELECTORS['remember_me'], timeout=3)
                if not remember_me.is_selected():
                    remember_me.click()
                    self.browser.human_like_delay(0.5, 1)
            except NoSuchElementException:
                logger.debug("Remember me checkbox not found")
            
            # Click login button
            login_button = self._find_element_by_selectors(self.LOGIN_SELECTORS['login_button'])
            self.browser.human_mouse_movement(login_button)
            login_button.click()
            
            # Wait for login to complete
            self.browser.human_like_delay(3, 6)
            
            # Check for login errors
            try:
                error_element = self._find_element_by_selectors(self.LOGIN_SELECTORS['error_message'], timeout=3)
                error_text = error_element.text
                logger.error(f"Login failed: {error_text}")
                raise AuthenticationError(f"CARFAX login failed: {error_text}")
            except NoSuchElementException:
                # No error message found, likely successful
                pass
            
            # Verify login success
            if self._check_login_status():
                self.is_logged_in = True
                self._save_session()
                logger.info("Successfully logged into CARFAX dealer portal")
                return True
            else:
                raise AuthenticationError("Login appeared to succeed but verification failed")
                
        except Exception as e:
            logger.error(f"CARFAX login failed: {e}")
            raise
    
    def _human_like_delay_with_variance(self, base_seconds: float = 5.0):
        """Add human-like delay with random variance"""
        delay = random.uniform(base_seconds * 0.7, base_seconds * 1.3)
        time.sleep(delay)
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=3, max=8),
        retry=retry_if_exception_type((TimeoutException, WebDriverException))
    )
    def lookup_vin(self, vin: str) -> Dict[str, any]:
        """Lookup vehicle history by VIN"""
        if not self.is_logged_in:
            if not self.login():
                raise AuthenticationError("Must be logged in to lookup VIN")
        
        # Validate VIN format
        vin = vin.upper().strip()
        if not re.match(r'^[A-Z0-9]{17}$', vin):
            raise ValueError(f"Invalid VIN format: {vin}")
        
        logger.info(f"Looking up VIN: {vin}")
        
        try:
            # Apply rate limiting
            rate_limiter.wait_if_needed('carfax_dealer', self.rate_config)
            
            # Navigate to VIN lookup page or find VIN input on current page
            current_url = self.driver.current_url
            if 'vin' not in current_url.lower() and 'search' not in current_url.lower():
                # Try to find VIN lookup link or navigate to search page
                vin_lookup_url = urljoin(self.DEALER_PORTAL_BASE, self.VIN_LOOKUP_PATH)
                self.driver.get(vin_lookup_url)
                self._human_like_delay_with_variance(3)
            
            # Find VIN input field
            vin_input = self._find_element_by_selectors(self.VIN_SELECTORS['vin_input'])
            vin_input.clear()
            
            # Type VIN with human-like delays
            for char in vin:
                vin_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            self._human_like_delay_with_variance(2)
            
            # Click search button
            search_button = self._find_element_by_selectors(self.VIN_SELECTORS['search_button'])
            self.browser.human_mouse_movement(search_button)
            search_button.click()
            
            # Wait for report to load
            self._human_like_delay_with_variance(8)
            
            # Wait for report container to appear
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ','.join(self.VIN_SELECTORS['report_container'])))
            )
            
            # Parse the report
            report_data = self._parse_vehicle_report(vin)
            
            # Record request for rate limiting
            rate_limiter.record_request('carfax_dealer')
            
            return report_data
            
        except Exception as e:
            logger.error(f"VIN lookup failed for {vin}: {e}")
            raise
    
    def _parse_vehicle_report(self, vin: str) -> Dict[str, any]:
        """Parse vehicle history report from the page"""
        logger.info(f"Parsing vehicle report for VIN: {vin}")
        
        try:
            # Get page source for BeautifulSoup parsing
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            report_data = {
                'vin': vin,
                'source': 'carfax_dealer_portal',
                'timestamp': datetime.now().isoformat(),
                'url': self.driver.current_url,
                'vehicle_info': {},
                'summary': {},
                'records': [],
                'flags': []
            }
            
            # Parse vehicle basic information
            report_data['vehicle_info'] = self._extract_vehicle_info(soup)
            
            # Parse accident information
            accident_count = self._extract_accident_count(soup)
            report_data['summary']['accident_count'] = accident_count
            
            # Parse service records
            service_records = self._extract_service_records(soup)
            report_data['records'] = service_records
            report_data['summary']['service_records_count'] = len(service_records)
            
            # Parse ownership history
            ownership_info = self._extract_ownership_history(soup)
            report_data['summary']['previous_owners'] = ownership_info.get('owner_count', 0)
            report_data['ownership_history'] = ownership_info
            
            # Parse title issues
            title_issues = self._extract_title_issues(soup)
            report_data['summary']['title_issues'] = title_issues
            
            # Extract any red flags from the text
            report_data['flags'] = self._extract_flags_from_text(page_source)
            
            logger.info(f"Successfully parsed report for VIN {vin}")
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to parse vehicle report: {e}")
            # Return basic structure with error info
            return {
                'vin': vin,
                'source': 'carfax_dealer_portal',
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'vehicle_info': {},
                'summary': {},
                'records': [],
                'flags': []
            }
    
    def _extract_vehicle_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract basic vehicle information"""
        vehicle_info = {}
        
        try:
            # Try multiple selectors for each field
            for field, selectors in self.REPORT_SELECTORS['vehicle_info'].items():
                for selector in selectors:
                    try:
                        element = soup.select_one(selector)
                        if element:
                            vehicle_info[field] = element.get_text(strip=True)
                            break
                    except Exception:
                        continue
            
            # Fallback: extract from page title or headers
            if not vehicle_info:
                title = soup.find('title')
                if title:
                    title_text = title.get_text()
                    # Try to extract year, make, model from title
                    match = re.search(r'(\d{4})\s+([A-Za-z]+)\s+([A-Za-z0-9\s]+)', title_text)
                    if match:
                        vehicle_info['year'] = match.group(1)
                        vehicle_info['make'] = match.group(2)
                        vehicle_info['model'] = match.group(3).strip()
            
        except Exception as e:
            logger.debug(f"Error extracting vehicle info: {e}")
        
        return vehicle_info
    
    def _extract_accident_count(self, soup: BeautifulSoup) -> int:
        """Extract accident count from report"""
        try:
            for selector in self.REPORT_SELECTORS['accident_count']:
                try:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        # Extract number from text
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            return int(numbers[0])
                except Exception:
                    continue
            
            # Fallback: search for accident-related text
            page_text = soup.get_text().lower()
            accident_patterns = [
                r'(\d+)\s+accident',
                r'(\d+)\s+reported\s+accident',
                r'accident.*?(\d+)',
                r'(\d+).*?accident'
            ]
            
            for pattern in accident_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    return int(matches[0])
            
            # Check for "no accidents" indicators
            if any(phrase in page_text for phrase in ['no accident', 'no reported accident', '0 accident']):
                return 0
                
        except Exception as e:
            logger.debug(f"Error extracting accident count: {e}")
        
        return 0
    
    def _extract_service_records(self, soup: BeautifulSoup) -> List[Dict[str, any]]:
        """Extract service records from report"""
        records = []
        
        try:
            # Look for service record containers
            for selector in self.REPORT_SELECTORS['service_records']:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        record = self._parse_service_record_element(element)
                        if record:
                            records.append(record)
                except Exception:
                    continue
            
            # If no structured records found, try to extract from text
            if not records:
                records = self._extract_service_records_from_text(soup.get_text())
                
        except Exception as e:
            logger.debug(f"Error extracting service records: {e}")
        
        return records
    
    def _parse_service_record_element(self, element) -> Optional[Dict[str, any]]:
        """Parse individual service record element"""
        try:
            record = {}
            
            # Extract date
            date_text = element.get_text()
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})', date_text)
            if date_match:
                record['date'] = date_match.group(1)
            
            # Extract odometer
            odometer_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:mile|mi)', date_text, re.IGNORECASE)
            if odometer_match:
                record['odometer'] = int(odometer_match.group(1).replace(',', ''))
            
            # Extract service description
            record['description'] = element.get_text(strip=True)
            
            # Categorize service type
            text_lower = date_text.lower()
            if any(word in text_lower for word in ['oil', 'maintenance', 'service', 'inspection']):
                record['type'] = 'maintenance'
            elif any(word in text_lower for word in ['accident', 'collision', 'damage', 'repair']):
                record['type'] = 'accident'
            elif any(word in text_lower for word in ['recall', 'safety']):
                record['type'] = 'recall'
            else:
                record['type'] = 'other'
            
            return record if record.get('date') or record.get('odometer') else None
            
        except Exception as e:
            logger.debug(f"Error parsing service record: {e}")
            return None
    
    def _extract_service_records_from_text(self, text: str) -> List[Dict[str, any]]:
        """Extract service records from plain text"""
        records = []
        
        try:
            # Look for date patterns followed by service descriptions
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for date patterns
                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})', line)
                if date_match:
                    record = {
                        'date': date_match.group(1),
                        'description': line,
                        'type': 'service'
                    }
                    
                    # Extract odometer if present
                    odometer_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:mile|mi)', line, re.IGNORECASE)
                    if odometer_match:
                        record['odometer'] = int(odometer_match.group(1).replace(',', ''))
                    
                    records.append(record)
                    
        except Exception as e:
            logger.debug(f"Error extracting service records from text: {e}")
        
        return records
    
    def _extract_ownership_history(self, soup: BeautifulSoup) -> Dict[str, any]:
        """Extract ownership history information"""
        ownership_info = {'owner_count': 0, 'details': []}
        
        try:
            # Look for ownership indicators
            page_text = soup.get_text().lower()
            
            # Extract owner count
            owner_patterns = [
                r'(\d+)\s+owner',
                r'(\d+)\s+previous\s+owner',
                r'owner.*?(\d+)',
                r'(\d+).*?owner'
            ]
            
            for pattern in owner_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    ownership_info['owner_count'] = int(matches[0])
                    break
            
            # Look for ownership details
            for selector in self.REPORT_SELECTORS['ownership_history']:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        detail = element.get_text(strip=True)
                        if detail:
                            ownership_info['details'].append(detail)
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error extracting ownership history: {e}")
        
        return ownership_info
    
    def _extract_title_issues(self, soup: BeautifulSoup) -> List[str]:
        """Extract title issues from report"""
        title_issues = []
        
        try:
            # Look for title issue elements
            for selector in self.REPORT_SELECTORS['title_issues']:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        issue = element.get_text(strip=True)
                        if issue:
                            title_issues.append(issue)
                except Exception:
                    continue
            
            # Search for title issue keywords in text
            page_text = soup.get_text().lower()
            title_keywords = [
                'flood', 'lemon', 'salvage', 'total loss', 'rebuilt', 
                'junk', 'fire damage', 'hail damage', 'theft recovery'
            ]
            
            for keyword in title_keywords:
                if keyword in page_text:
                    title_issues.append(keyword.title())
                    
        except Exception as e:
            logger.debug(f"Error extracting title issues: {e}")
        
        return list(set(title_issues))  # Remove duplicates
    
    def _extract_flags_from_text(self, page_source: str) -> List[str]:
        """Extract red flags from page text"""
        flags = []
        
        try:
            text_lower = page_source.lower()
            
            # Define flag patterns
            flag_patterns = {
                'Odometer rollback': ['rollback', 'odometer discrepancy'],
                'Frame damage': ['frame damage', 'structural damage'],
                'Airbag deployment': ['airbag deploy', 'airbag replacement'],
                'Multiple accidents': ['multiple accident', 'several accident'],
                'Commercial use': ['taxi', 'rental', 'fleet', 'commercial'],
                'Auction vehicle': ['auction', 'wholesale'],
                'Manufacturer buyback': ['buyback', 'lemon law'],
            }
            
            for flag_name, keywords in flag_patterns.items():
                if any(keyword in text_lower for keyword in keywords):
                    flags.append(flag_name)
                    
        except Exception as e:
            logger.debug(f"Error extracting flags: {e}")
        
        return flags
    
    def close(self):
        """Close browser and cleanup"""
        if self.browser:
            self.browser.quit()
            self.browser = None
            self.driver = None
            self.is_logged_in = False


class CarfaxIntegrator:
    """
    Enhanced Carfax vehicle history integration using dealer portal web scraping
    """
    
    def __init__(self):
        self.scraper = CarfaxDealerPortalScraper()
        
        # Legacy API support (fallback)
        carfax_config = config.get_integration_config('carfax')
        self.api_key = carfax_config.get('api_key')
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def get_vehicle_history(self, vin: str) -> Dict[str, any]:
        """Get comprehensive vehicle history report"""
        try:
            # Primary method: Use dealer portal scraping
            if self.scraper.username and self.scraper.password:
                logger.info(f"Fetching CARFAX history for VIN {vin} using dealer portal")
                return self.scraper.lookup_vin(vin)
            
            # Fallback: Try legacy API if available
            elif self.api_key:
                logger.info(f"Falling back to legacy API for VIN {vin}")
                return self._get_history_api(vin)
            
            else:
                logger.warning("No CARFAX access method configured")
                return {}
                
        except Exception as e:
            logger.error(f"Carfax history lookup failed for {vin}: {e}")
            return {}
    
    def _get_history_api(self, vin: str) -> Optional[Dict[str, any]]:
        """Get history using legacy Carfax API (fallback)"""
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
    
    def analyze_history_flags(self, history_data: Dict[str, any]) -> Dict[str, any]:
        """Analyze history data for red flags"""
        flags = {
            'red_flags': [],
            'yellow_flags': [],
            'green_flags': [],
            'overall_risk': 'unknown'
        }
        
        try:
            if history_data.get('source') == 'carfax_dealer_portal':
                flags = self._analyze_dealer_portal_data(history_data, flags)
            else:
                # Legacy analysis for API data
                summary = history_data.get('summary', {})
                flags = self._analyze_summary_data(summary, flags)
            
        except Exception as e:
            logger.error(f"History analysis failed: {e}")
        
        return flags
    
    def _analyze_dealer_portal_data(self, history_data: Dict[str, any], flags: Dict[str, any]) -> Dict[str, any]:
        """Analyze data from dealer portal scraping"""
        try:
            summary = history_data.get('summary', {})
            records = history_data.get('records', [])
            extracted_flags = history_data.get('flags', [])
            title_issues = summary.get('title_issues', [])
            
            # Red flags
            accident_count = summary.get('accident_count', 0)
            if accident_count > 2:
                flags['red_flags'].append(f"Multiple accidents reported ({accident_count})")
            
            if title_issues:
                for issue in title_issues:
                    if any(keyword in issue.lower() for keyword in ['flood', 'lemon', 'salvage', 'total loss']):
                        flags['red_flags'].append(f"Title issue: {issue}")
            
            # Add extracted flags as red flags
            flags['red_flags'].extend(extracted_flags)
            
            previous_owners = summary.get('previous_owners', 0)
            if previous_owners > 4:
                flags['red_flags'].append(f"Many previous owners ({previous_owners})")
            
            # Yellow flags
            if accident_count == 1:
                flags['yellow_flags'].append("One reported accident")
            
            service_count = summary.get('service_records_count', 0)
            if service_count < 3:
                flags['yellow_flags'].append("Limited service history")
            
            if previous_owners == 3 or previous_owners == 4:
                flags['yellow_flags'].append(f"Multiple previous owners ({previous_owners})")
            
            # Green flags
            if accident_count == 0:
                flags['green_flags'].append("No reported accidents")
            
            if service_count > 10:
                flags['green_flags'].append("Extensive service history")
            
            if previous_owners <= 2:
                flags['green_flags'].append("Few previous owners")
            
            if not title_issues and not extracted_flags:
                flags['green_flags'].append("No title issues found")
            
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
            logger.error(f"Dealer portal data analysis failed: {e}")
        
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
        """Close scraper and cleanup"""
        if self.scraper:
            self.scraper.close()
