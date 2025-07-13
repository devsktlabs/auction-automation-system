
import requests
from typing import Dict, List, Optional
from utils.config import config
from utils.logger import logger
from utils.errors import IntegrationError

class DealersLinkIntegrator:
    """DealersLink integration for vehicle appraisals and marketplace data"""
    
    def __init__(self):
        self.base_url = "https://public.dealerslink.com"
        self.api_key = config.get_integration_config('dealerslink').get('api_key')
        self.username = config.get_integration_config('dealerslink').get('username')
        self.password = config.get_integration_config('dealerslink').get('password')
        self.session = requests.Session()
        self.authenticated = False
        
        if self.api_key:
            self._authenticate_api()
        elif self.username and self.password:
            self._authenticate_credentials()
    
    def _authenticate_api(self):
        """Authenticate using API key"""
        try:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
            self.authenticated = True
            logger.info("DealersLink API authentication successful")
            
        except Exception as e:
            logger.error(f"DealersLink API authentication failed: {e}")
            raise IntegrationError(f"Authentication failed: {e}")
    
    def _authenticate_credentials(self):
        """Authenticate using username/password"""
        try:
            auth_url = f"{self.base_url}/api/auth"
            credentials = {
                'username': self.username,
                'password': self.password
            }
            
            response = self.session.post(auth_url, json=credentials)
            
            if response.status_code == 200:
                token = response.json().get('token')
                self.session.headers.update({'Authorization': f'Bearer {token}'})
                self.authenticated = True
                logger.info("DealersLink credential authentication successful")
            else:
                raise IntegrationError(f"Authentication failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"DealersLink credential authentication failed: {e}")
            raise IntegrationError(f"Authentication failed: {e}")
    
    def get_vehicle_appraisal(self, vin: str) -> Dict[str, any]:
        """Get comprehensive vehicle appraisal"""
        if not self.authenticated:
            logger.warning("DealersLink not authenticated, skipping appraisal")
            return {}
        
        try:
            appraisal_url = f"{self.base_url}/api/appraisal"
            
            payload = {
                'vin': vin,
                'include_oem_data': True,
                'include_market_data': True,
                'include_condition_adjustments': True
            }
            
            response = self.session.post(appraisal_url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"No appraisal data found for VIN: {vin}")
                return {}
            else:
                logger.warning(f"Appraisal request failed: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"DealersLink appraisal failed for {vin}: {e}")
            return {}
    
    def search_marketplace(self, criteria: Dict[str, any]) -> List[Dict[str, any]]:
        """Search dealer-to-dealer marketplace"""
        if not self.authenticated:
            logger.warning("DealersLink not authenticated, skipping marketplace search")
            return []
        
        try:
            search_url = f"{self.base_url}/api/marketplace/search"
            
            # Convert criteria to DealersLink format
            search_criteria = {
                'year_min': criteria.get('year_min'),
                'year_max': criteria.get('year_max'),
                'make': criteria.get('make'),
                'model': criteria.get('model'),
                'mileage_max': criteria.get('mileage_max'),
                'price_max': criteria.get('price_max'),
                'radius_miles': criteria.get('radius_miles', 500),
                'zip_code': criteria.get('zip_code', '10001')
            }
            
            # Remove None values
            search_criteria = {k: v for k, v in search_criteria.items() if v is not None}
            
            response = self.session.post(search_url, json=search_criteria)
            
            if response.status_code == 200:
                return response.json().get('listings', [])
            else:
                logger.warning(f"Marketplace search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"DealersLink marketplace search failed: {e}")
            return []
    
    def get_market_insights(self, vin: str) -> Dict[str, any]:
        """Get market insights and pricing trends"""
        if not self.authenticated:
            return {}
        
        try:
            insights_url = f"{self.base_url}/api/market/insights"
            
            payload = {'vin': vin}
            response = self.session.post(insights_url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Market insights failed for {vin}: {e}")
            return {}
    
    def get_stocking_recommendations(self, market_area: str) -> Dict[str, any]:
        """Get AI-powered stocking recommendations"""
        if not self.authenticated:
            return {}
        
        try:
            recommend_url = f"{self.base_url}/api/recommendations/stocking"
            
            params = {
                'market_area': market_area,
                'velocity_months': 12,
                'include_trends': True
            }
            
            response = self.session.get(recommend_url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Stocking recommendations failed: {e}")
            return {}
    
    def analyze_deal_potential(self, vehicle_data: Dict[str, any], current_bid: float) -> Dict[str, any]:
        """Analyze deal potential based on DealersLink data"""
        analysis = {
            'deal_score': 0,
            'profit_potential': 'unknown',
            'market_position': 'unknown',
            'recommendations': []
        }
        
        try:
            # Get appraisal data
            vin = vehicle_data.get('vin')
            if not vin:
                return analysis
            
            appraisal = self.get_vehicle_appraisal(vin)
            if not appraisal:
                return analysis
            
            # Extract key values
            trade_value = appraisal.get('trade_value', 0)
            retail_value = appraisal.get('retail_value', 0)
            wholesale_value = appraisal.get('wholesale_value', 0)
            
            if trade_value and current_bid:
                # Calculate potential profit margins
                trade_margin = trade_value - current_bid
                retail_margin = retail_value - current_bid
                wholesale_margin = wholesale_value - current_bid
                
                # Deal scoring (0-100)
                if trade_margin > 3000:
                    analysis['deal_score'] = 90
                    analysis['profit_potential'] = 'excellent'
                elif trade_margin > 2000:
                    analysis['deal_score'] = 75
                    analysis['profit_potential'] = 'good'
                elif trade_margin > 1000:
                    analysis['deal_score'] = 60
                    analysis['profit_potential'] = 'fair'
                elif trade_margin > 0:
                    analysis['deal_score'] = 40
                    analysis['profit_potential'] = 'marginal'
                else:
                    analysis['deal_score'] = 20
                    analysis['profit_potential'] = 'poor'
                
                # Market position
                if current_bid < wholesale_value * 0.8:
                    analysis['market_position'] = 'below_market'
                elif current_bid < wholesale_value:
                    analysis['market_position'] = 'at_wholesale'
                elif current_bid < retail_value * 0.9:
                    analysis['market_position'] = 'fair_market'
                else:
                    analysis['market_position'] = 'above_market'
                
                # Recommendations
                if analysis['deal_score'] >= 75:
                    analysis['recommendations'].append("Strong buy recommendation")
                elif analysis['deal_score'] >= 60:
                    analysis['recommendations'].append("Consider bidding with caution")
                else:
                    analysis['recommendations'].append("Avoid - insufficient margin")
                
                analysis['trade_margin'] = trade_margin
                analysis['retail_margin'] = retail_margin
                analysis['wholesale_margin'] = wholesale_margin
            
        except Exception as e:
            logger.error(f"Deal analysis failed: {e}")
        
        return analysis
