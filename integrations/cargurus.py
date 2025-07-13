
import requests
import time
import random
from typing import Dict, List, Optional
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import re

from automation.browser import StealthBrowser
from utils.config import config
from utils.logger import logger
from utils.rate_limiter import rate_limiter, RateLimitConfig
from utils.errors import IntegrationError

class CarGurusIntegrator:
    """CarGurus integration for market pricing and vehicle listings"""
    
    def __init__(self):
        self.base_url = "https://www.cargurus.com"
        self.session = requests.Session()
        self.browser = None
        self.rate_config = RateLimitConfig(
            requests_per_minute=12,
            burst_limit=4,
            cooldown_seconds=5
        )
        
        # Setup session headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        })
    
    def search_by_vin(self, vin: str) -> Optional[Dict[str, any]]:
        """Search CarGurus for specific VIN"""
        try:
            # Rate limiting
            rate_limiter.wait_if_needed('cargurus', self.rate_config)
            
            search_url = f"{self.base_url}/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action"
            
            params = {
                'vin': vin,
                'zip': '10001',  # Default NYC zip
                'distance': 'ALL'
            }
            
            response = self.session.get(search_url, params=params)
            
            if response.status_code == 200:
                vehicle_data = self._parse_vehicle_data(response.text, vin)
                rate_limiter.record_request('cargurus')
                return vehicle_data
            
            return None
            
        except Exception as e:
            logger.error(f"CarGurus VIN search failed for {vin}: {e}")
            return None
    
    def get_market_analysis(self, year: int, make: str, model: str, 
                          mileage: int, zip_code: str = "10001") -> Dict[str, any]:
        """Get market analysis for vehicle specifications"""
        try:
            # Rate limiting
            rate_limiter.wait_if_needed('cargurus', self.rate_config)
            
            analysis_url = f"{self.base_url}/Cars/price-analysis"
            
            params = {
                'year': year,
                'make': make,
                'model': model,
                'mileage': mileage,
                'zip': zip_code
            }
            
            response = self.session.get(analysis_url, params=params)
            
            if response.status_code == 200:
                analysis = self._parse_market_analysis(response.text)
                rate_limiter.record_request('cargurus')
                return analysis
            
            return {}
            
        except Exception as e:
            logger.error(f"CarGurus market analysis failed: {e}")
            return {}
    
    def get_imv_scan(self, vin: str) -> Dict[str, any]:
        """Get Instant Market Value scan for VIN"""
        try:
            if not self.browser:
                self.browser = StealthBrowser("cargurus")
                self.driver = self.browser.create_stealth_driver()
            
            # Rate limiting
            rate_limiter.wait_if_needed('cargurus', self.rate_config)
            
            # Navigate to IMV scan page
            imv_url = f"{self.base_url}/Cars/imv-scan"
            self.driver.get(imv_url)
            
            # Wait for page load
            time.sleep(random.uniform(2, 4))
            
            # Enter VIN
            vin_input = self.driver.find_element(By.NAME, "vin")
            vin_input.clear()
            vin_input.send_keys(vin)
            
            # Submit
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # Wait for results
            time.sleep(random.uniform(3, 6))
            
            # Extract IMV data
            imv_data = self._extract_imv_data()
            
            rate_limiter.record_request('cargurus')
            return imv_data
            
        except Exception as e:
            logger.error(f"CarGurus IMV scan failed for {vin}: {e}")
            return {}
    
    def search_similar_vehicles(self, criteria: Dict[str, any]) -> List[Dict[str, any]]:
        """Search for similar vehicles in the market"""
        try:
            # Rate limiting
            rate_limiter.wait_if_needed('cargurus', self.rate_config)
            
            search_url = f"{self.base_url}/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action"
            
            params = {
                'sourceContext': 'carGurusHomePageModel',
                'entitySelectingHelper.selectedEntity': f"{criteria.get('year', '')} {criteria.get('make', '')} {criteria.get('model', '')}",
                'zip': criteria.get('zip_code', '10001'),
                'distance': criteria.get('distance', '500'),
                'maxPrice': criteria.get('max_price', ''),
                'maxMileage': criteria.get('max_mileage', ''),
                'minYear': criteria.get('min_year', ''),
                'maxYear': criteria.get('max_year', '')
            }
            
            # Remove empty parameters
            params = {k: v for k, v in params.items() if v}
            
            response = self.session.get(search_url, params=params)
            
            if response.status_code == 200:
                vehicles = self._parse_search_results(response.text)
                rate_limiter.record_request('cargurus')
                return vehicles
            
            return []
            
        except Exception as e:
            logger.error(f"CarGurus similar vehicle search failed: {e}")
            return []
    
    def _parse_vehicle_data(self, html_content: str, vin: str) -> Optional[Dict[str, any]]:
        """Parse vehicle data from HTML response"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract vehicle details
            title_elem = soup.find('h1', class_='listing-title')
            if not title_elem:
                return None
                
            title = title_elem.text.strip()
            year, make, model = self._parse_vehicle_title(title)
            
            # Extract price
            price_elem = soup.find('span', class_='price-section')
            price = self._parse_price(price_elem.text if price_elem else "0")
            
            # Extract mileage
            mileage_elem = soup.find('span', class_='listing-mileage')
            mileage = self._parse_mileage(mileage_elem.text if mileage_elem else "0")
            
            # Extract dealer info
            dealer_elem = soup.find('span', class_='dealer-name')
            dealer_name = dealer_elem.text.strip() if dealer_elem else "Unknown"
            
            # Extract deal rating
            rating_elem = soup.find('span', class_='deal-rating')
            deal_rating = rating_elem.text.strip() if rating_elem else "No Rating"
            
            # Extract IMV
            imv_elem = soup.find('span', class_='imv-price')
            imv_price = self._parse_price(imv_elem.text if imv_elem else "0")
            
            return {
                'vin': vin,
                'year': year,
                'make': make,
                'model': model,
                'mileage': mileage,
                'price': price,
                'dealer_name': dealer_name,
                'deal_rating': deal_rating,
                'imv_price': imv_price,
                'source': 'cargurus'
            }
            
        except Exception as e:
            logger.error(f"Error parsing CarGurus vehicle data: {e}")
            return None
    
    def _parse_market_analysis(self, html_content: str) -> Dict[str, any]:
        """Parse market analysis from HTML"""
        analysis = {}
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract average price
            avg_price_elem = soup.find('span', class_='average-price')
            if avg_price_elem:
                analysis['average_price'] = self._parse_price(avg_price_elem.text)
            
            # Extract price range
            price_range_elem = soup.find('div', class_='price-range')
            if price_range_elem:
                range_text = price_range_elem.text
                analysis['price_range'] = range_text
            
            # Extract market trends
            trend_elem = soup.find('div', class_='market-trend')
            if trend_elem:
                analysis['market_trend'] = trend_elem.text.strip()
            
            # Extract days on market
            dom_elem = soup.find('span', class_='days-on-market')
            if dom_elem:
                analysis['avg_days_on_market'] = dom_elem.text.strip()
            
        except Exception as e:
            logger.error(f"Market analysis parsing failed: {e}")
        
        return analysis
    
    def _extract_imv_data(self) -> Dict[str, any]:
        """Extract IMV data from current page"""
        imv_data = {}
        
        try:
            # IMV value
            try:
                imv_value_elem = self.driver.find_element(By.CSS_SELECTOR, ".imv-value")
                imv_data['imv_value'] = self._parse_price(imv_value_elem.text)
            except NoSuchElementException:
                pass
            
            # IMV range
            try:
                imv_range_elem = self.driver.find_element(By.CSS_SELECTOR, ".imv-range")
                imv_data['imv_range'] = imv_range_elem.text.strip()
            except NoSuchElementException:
                pass
            
            # Market position
            try:
                position_elem = self.driver.find_element(By.CSS_SELECTOR, ".market-position")
                imv_data['market_position'] = position_elem.text.strip()
            except NoSuchElementException:
                pass
            
            # Confidence score
            try:
                confidence_elem = self.driver.find_element(By.CSS_SELECTOR, ".confidence-score")
                imv_data['confidence_score'] = confidence_elem.text.strip()
            except NoSuchElementException:
                pass
            
        except Exception as e:
            logger.error(f"IMV data extraction failed: {e}")
        
        return imv_data
    
    def _parse_search_results(self, html_content: str) -> List[Dict[str, any]]:
        """Parse search results from HTML"""
        vehicles = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find vehicle listings
            listing_elements = soup.find_all('div', class_='vehicle-listing')
            
            for listing in listing_elements:
                try:
                    vehicle_data = {}
                    
                    # Title
                    title_elem = listing.find('h3', class_='listing-title')
                    if title_elem:
                        title = title_elem.text.strip()
                        year, make, model = self._parse_vehicle_title(title)
                        vehicle_data.update({'year': year, 'make': make, 'model': model})
                    
                    # Price
                    price_elem = listing.find('span', class_='listing-price')
                    if price_elem:
                        vehicle_data['price'] = self._parse_price(price_elem.text)
                    
                    # Mileage
                    mileage_elem = listing.find('span', class_='listing-mileage')
                    if mileage_elem:
                        vehicle_data['mileage'] = self._parse_mileage(mileage_elem.text)
                    
                    # Deal rating
                    rating_elem = listing.find('span', class_='deal-rating')
                    if rating_elem:
                        vehicle_data['deal_rating'] = rating_elem.text.strip()
                    
                    # Location
                    location_elem = listing.find('span', class_='listing-location')
                    if location_elem:
                        vehicle_data['location'] = location_elem.text.strip()
                    
                    if vehicle_data:
                        vehicles.append(vehicle_data)
                        
                except Exception as e:
                    logger.debug(f"Failed to parse individual listing: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Search results parsing failed: {e}")
        
        return vehicles
    
    def _parse_vehicle_title(self, title: str) -> tuple:
        """Parse year, make, model from title"""
        parts = title.split()
        
        if len(parts) >= 3:
            year = int(parts[0]) if parts[0].isdigit() else 0
            make = parts[1]
            model = parts[2]
            return year, make, model
        
        return 0, '', ''
    
    def _parse_price(self, text: str) -> float:
        """Parse price from text"""
        cleaned = re.sub(r'[^\d.]', '', text)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _parse_mileage(self, text: str) -> int:
        """Parse mileage from text"""
        cleaned = re.sub(r'[^\d]', '', text)
        try:
            return int(cleaned)
        except ValueError:
            return 0
    
    def analyze_market_position(self, vehicle_data: Dict[str, any], current_bid: float) -> Dict[str, any]:
        """Analyze vehicle's market position"""
        analysis = {
            'market_position': 'unknown',
            'price_competitiveness': 'unknown',
            'recommendations': []
        }
        
        try:
            # Get market data for similar vehicles
            similar_vehicles = self.search_similar_vehicles({
                'year': vehicle_data.get('year'),
                'make': vehicle_data.get('make'),
                'model': vehicle_data.get('model'),
                'max_mileage': vehicle_data.get('mileage', 0) + 10000,
                'zip_code': '10001'
            })
            
            if similar_vehicles:
                prices = [v.get('price', 0) for v in similar_vehicles if v.get('price', 0) > 0]
                
                if prices:
                    avg_market_price = sum(prices) / len(prices)
                    min_price = min(prices)
                    max_price = max(prices)
                    
                    # Analyze current bid position
                    if current_bid < min_price:
                        analysis['market_position'] = 'well_below_market'
                        analysis['price_competitiveness'] = 'excellent'
                        analysis['recommendations'].append("Excellent deal - well below market")
                    elif current_bid < avg_market_price * 0.9:
                        analysis['market_position'] = 'below_market'
                        analysis['price_competitiveness'] = 'good'
                        analysis['recommendations'].append("Good deal - below average market price")
                    elif current_bid < avg_market_price * 1.1:
                        analysis['market_position'] = 'at_market'
                        analysis['price_competitiveness'] = 'fair'
                        analysis['recommendations'].append("Fair price - at market average")
                    else:
                        analysis['market_position'] = 'above_market'
                        analysis['price_competitiveness'] = 'poor'
                        analysis['recommendations'].append("Overpriced - above market average")
                    
                    analysis['market_stats'] = {
                        'average_price': avg_market_price,
                        'price_range': f"${min_price:,.0f} - ${max_price:,.0f}",
                        'sample_size': len(prices)
                    }
            
        except Exception as e:
            logger.error(f"Market position analysis failed: {e}")
        
        return analysis
    
    def close(self):
        """Close browser if open"""
        if self.browser:
            self.browser.quit()
