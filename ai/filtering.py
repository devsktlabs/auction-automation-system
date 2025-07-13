
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from utils.config import config
from utils.logger import logger

@dataclass
class FilteringCriteria:
    """User's filtering criteria for vehicle selection"""
    # Avoid criteria
    avoid_transmission_flush: bool = True
    avoid_major_electrical_issues: bool = True
    avoid_major_transmission_issues: bool = True
    avoid_major_engine_issues: bool = True
    avoid_non_working_headlights: bool = True
    
    # Prefer criteria
    prefer_minor_paint_work: bool = True
    prefer_minor_body_work: bool = True
    prefer_working_headlights: bool = True
    prefer_obd2_ready: bool = True
    
    # Price and specifications
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    max_mileage: Optional[int] = None
    min_year: Optional[int] = None

class VehicleFilteringEngine:
    """Intelligent vehicle filtering based on user criteria and AI analysis"""
    
    def __init__(self):
        self.criteria = self._load_filtering_criteria()
        
    def _load_filtering_criteria(self) -> FilteringCriteria:
        """Load filtering criteria from configuration"""
        config_criteria = config.get('filtering', {})
        
        return FilteringCriteria(
            min_price=config_criteria.get('price_range', {}).get('min'),
            max_price=config_criteria.get('price_range', {}).get('max'),
            max_mileage=config_criteria.get('mileage_range', {}).get('max'),
            min_year=config_criteria.get('year_range', {}).get('min')
        )
    
    def evaluate_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive vehicle evaluation against user criteria"""
        evaluation = {
            'vehicle_id': vehicle_data.get('vin', 'unknown'),
            'overall_score': 0,
            'recommendation': 'unknown',
            'meets_criteria': True,
            'violations': [],
            'positive_factors': [],
            'concerns': [],
            'detailed_scores': {},
            'bid_recommendation': {}
        }
        
        try:
            # Basic specifications check
            spec_score = self._evaluate_specifications(vehicle_data)
            evaluation['detailed_scores']['specifications'] = spec_score
            
            # OBD2 analysis evaluation
            obd2_score = self._evaluate_obd2_analysis(vehicle_data)
            evaluation['detailed_scores']['obd2'] = obd2_score
            
            # Dashboard lights evaluation
            dashboard_score = self._evaluate_dashboard_lights(vehicle_data)
            evaluation['detailed_scores']['dashboard'] = dashboard_score
            
            # Image analysis evaluation
            image_score = self._evaluate_image_analysis(vehicle_data)
            evaluation['detailed_scores']['image_analysis'] = image_score
            
            # Market analysis evaluation
            market_score = self._evaluate_market_analysis(vehicle_data)
            evaluation['detailed_scores']['market_analysis'] = market_score
            
            # History analysis evaluation
            history_score = self._evaluate_history_analysis(vehicle_data)
            evaluation['detailed_scores']['history'] = history_score
            
            # Calculate overall score
            evaluation['overall_score'] = self._calculate_overall_score(evaluation['detailed_scores'])
            
            # Determine recommendation
            evaluation['recommendation'] = self._determine_recommendation(evaluation)
            
            # Generate bid recommendation
            evaluation['bid_recommendation'] = self._generate_bid_recommendation(vehicle_data, evaluation)
            
        except Exception as e:
            logger.error(f"Vehicle evaluation failed: {e}")
            evaluation['recommendation'] = 'error'
        
        return evaluation
    
    def _evaluate_specifications(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate basic vehicle specifications"""
        score_data = {
            'score': 100,
            'violations': [],
            'positive_factors': []
        }
        
        try:
            # Price range check
            current_bid = vehicle_data.get('current_bid', 0)
            if self.criteria.max_price and current_bid > self.criteria.max_price:
                score_data['violations'].append(f"Price ${current_bid:,} exceeds max ${self.criteria.max_price:,}")
                score_data['score'] -= 30
            
            if self.criteria.min_price and current_bid < self.criteria.min_price:
                score_data['violations'].append(f"Price ${current_bid:,} below min ${self.criteria.min_price:,}")
                score_data['score'] -= 10
            
            # Mileage check
            mileage = vehicle_data.get('mileage', 0)
            if self.criteria.max_mileage and mileage > self.criteria.max_mileage:
                score_data['violations'].append(f"Mileage {mileage:,} exceeds max {self.criteria.max_mileage:,}")
                score_data['score'] -= 20
            
            # Year check
            year = vehicle_data.get('year', 0)
            if self.criteria.min_year and year < self.criteria.min_year:
                score_data['violations'].append(f"Year {year} below minimum {self.criteria.min_year}")
                score_data['score'] -= 25
            
            # Positive factors
            if mileage < 50000:
                score_data['positive_factors'].append("Low mileage vehicle")
                score_data['score'] += 10
            
            if year >= 2020:
                score_data['positive_factors'].append("Recent model year")
                score_data['score'] += 5
            
        except Exception as e:
            logger.error(f"Specification evaluation failed: {e}")
        
        return score_data
    
    def _evaluate_obd2_analysis(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate OBD2 diagnostic analysis"""
        score_data = {
            'score': 100,
            'violations': [],
            'positive_factors': []
        }
        
        try:
            obd2_analysis = vehicle_data.get('obd2_analysis', {})
            
            # Critical issues check
            critical_issues = obd2_analysis.get('critical_issues', [])
            if critical_issues:
                score_data['violations'].append(f"Critical OBD2 issues: {len(critical_issues)}")
                score_data['score'] -= 50
            
            # Transmission issues (user's avoid criteria)
            system_analysis = obd2_analysis.get('system_analysis', {})
            transmission_issues = system_analysis.get('transmission', {})
            if transmission_issues:
                score_data['violations'].append("Transmission codes detected")
                score_data['score'] -= 40
            
            # Engine issues
            engine_issues = system_analysis.get('engine', {})
            if engine_issues and engine_issues.get('health_status') in ['critical', 'severe']:
                score_data['violations'].append("Major engine issues detected")
                score_data['score'] -= 35
            
            # Electrical issues
            electrical_issues = system_analysis.get('electrical', {})
            if electrical_issues and electrical_issues.get('health_status') in ['critical', 'severe']:
                score_data['violations'].append("Major electrical issues detected")
                score_data['score'] -= 30
            
            # Inspection readiness (user prefers OBD2 ready)
            readiness = obd2_analysis.get('inspection_readiness', 'unknown')
            if readiness in ['ready', 'ready_with_codes']:
                score_data['positive_factors'].append("OBD2 inspection ready")
                score_data['score'] += 10
            elif readiness in ['not_ready_emissions', 'not_ready_critical']:
                score_data['violations'].append("Not OBD2 inspection ready")
                score_data['score'] -= 15
            
            # No codes is good
            if obd2_analysis.get('overall_assessment') == 'no_codes':
                score_data['positive_factors'].append("No diagnostic codes present")
                score_data['score'] += 15
            
        except Exception as e:
            logger.error(f"OBD2 evaluation failed: {e}")
        
        return score_data
    
    def _evaluate_dashboard_lights(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate dashboard warning lights analysis"""
        score_data = {
            'score': 100,
            'violations': [],
            'positive_factors': []
        }
        
        try:
            dashboard_analysis = vehicle_data.get('dashboard_analysis', {})
            
            # Critical warnings
            critical_warnings = dashboard_analysis.get('critical_warnings', [])
            if critical_warnings:
                score_data['violations'].append(f"Critical dashboard warnings: {len(critical_warnings)}")
                score_data['score'] -= 40
            
            # Safety concerns
            safety_concerns = dashboard_analysis.get('safety_concerns', [])
            if safety_concerns:
                score_data['violations'].append(f"Safety system warnings: {len(safety_concerns)}")
                score_data['score'] -= 30
            
            # Headlight issues (user's specific criteria)
            system_analysis = dashboard_analysis.get('system_analysis', {})
            lighting_issues = system_analysis.get('lighting', {})
            if lighting_issues:
                # Check if headlight related
                lights = lighting_issues.get('lights', [])
                headlight_issues = [light for light in lights if 'headlight' in light.lower()]
                if headlight_issues:
                    score_data['violations'].append("Headlight warning detected")
                    score_data['score'] -= 25
            
            # Transmission warnings
            transmission_warnings = system_analysis.get('transmission', {})
            if transmission_warnings:
                score_data['violations'].append("Transmission warning lights")
                score_data['score'] -= 35
            
            # Engine warnings
            engine_warnings = system_analysis.get('engine', {})
            if engine_warnings and engine_warnings.get('health_status') in ['critical', 'severe']:
                score_data['violations'].append("Major engine warning lights")
                score_data['score'] -= 30
            
            # No warnings is excellent
            if dashboard_analysis.get('overall_assessment') == 'no_warnings':
                score_data['positive_factors'].append("No dashboard warning lights")
                score_data['score'] += 15
            
        except Exception as e:
            logger.error(f"Dashboard evaluation failed: {e}")
        
        return score_data
    
    def _evaluate_image_analysis(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate image analysis results"""
        score_data = {
            'score': 100,
            'violations': [],
            'positive_factors': []
        }
        
        try:
            image_analysis = vehicle_data.get('image_analysis', {})
            
            # Damage detection
            damage_detected = image_analysis.get('damage_detected', False)
            if damage_detected:
                detailed_analysis = image_analysis.get('detailed_analysis', [])
                severe_damages = []
                
                for analysis in detailed_analysis:
                    for damage in analysis.get('damages', []):
                        if damage.get('severity') in ['severe', 'moderate']:
                            severe_damages.append(damage['type'])
                
                if severe_damages:
                    score_data['violations'].append(f"Significant damage: {', '.join(set(severe_damages))}")
                    score_data['score'] -= 30
                else:
                    score_data['violations'].append("Minor damage detected")
                    score_data['score'] -= 10
            
            # Overall condition
            condition = image_analysis.get('overall_condition', 'unknown')
            condition_score = image_analysis.get('condition_score', 0)
            
            if condition == 'excellent':
                score_data['positive_factors'].append("Excellent visual condition")
                score_data['score'] += 15
            elif condition == 'good':
                score_data['positive_factors'].append("Good visual condition")
                score_data['score'] += 10
            elif condition == 'fair':
                score_data['violations'].append("Fair condition - reconditioning needed")
                score_data['score'] -= 15
            elif condition == 'poor':
                score_data['violations'].append("Poor condition - high reconditioning costs")
                score_data['score'] -= 30
            
            # User prefers minor paint/body work
            if condition in ['good', 'fair'] and not damage_detected:
                score_data['positive_factors'].append("Minor cosmetic work needed - user preference")
                score_data['score'] += 5
            
        except Exception as e:
            logger.error(f"Image analysis evaluation failed: {e}")
        
        return score_data
    
    def _evaluate_market_analysis(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate market analysis and pricing"""
        score_data = {
            'score': 100,
            'violations': [],
            'positive_factors': []
        }
        
        try:
            # CarGurus analysis
            cargurus_analysis = vehicle_data.get('cargurus_analysis', {})
            market_position = cargurus_analysis.get('market_position', 'unknown')
            
            if market_position == 'well_below_market':
                score_data['positive_factors'].append("Excellent deal - well below market")
                score_data['score'] += 20
            elif market_position == 'below_market':
                score_data['positive_factors'].append("Good deal - below market price")
                score_data['score'] += 15
            elif market_position == 'at_market':
                score_data['positive_factors'].append("Fair market price")
                score_data['score'] += 5
            elif market_position == 'above_market':
                score_data['violations'].append("Above market price")
                score_data['score'] -= 20
            
            # DealersLink analysis
            dealerslink_analysis = vehicle_data.get('dealerslink_analysis', {})
            profit_potential = dealerslink_analysis.get('profit_potential', 'unknown')
            
            if profit_potential == 'excellent':
                score_data['positive_factors'].append("Excellent profit potential")
                score_data['score'] += 15
            elif profit_potential == 'good':
                score_data['positive_factors'].append("Good profit potential")
                score_data['score'] += 10
            elif profit_potential == 'poor':
                score_data['violations'].append("Poor profit potential")
                score_data['score'] -= 25
            
        except Exception as e:
            logger.error(f"Market analysis evaluation failed: {e}")
        
        return score_data
    
    def _evaluate_history_analysis(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate vehicle history analysis"""
        score_data = {
            'score': 100,
            'violations': [],
            'positive_factors': []
        }
        
        try:
            # Carfax analysis
            carfax_analysis = vehicle_data.get('carfax_analysis', {})
            carfax_flags = carfax_analysis.get('flags', {})
            
            red_flags = carfax_flags.get('red_flags', [])
            if red_flags:
                score_data['violations'].append(f"Carfax red flags: {len(red_flags)}")
                score_data['score'] -= len(red_flags) * 10
            
            green_flags = carfax_flags.get('green_flags', [])
            if green_flags:
                score_data['positive_factors'].append(f"Positive history indicators: {len(green_flags)}")
                score_data['score'] += len(green_flags) * 3
            
            # AutoCheck analysis
            autocheck_analysis = vehicle_data.get('autocheck_analysis', {})
            autocheck_score_analysis = autocheck_analysis.get('score_analysis', {})
            
            risk_level = autocheck_score_analysis.get('risk_level', 'unknown')
            if risk_level == 'low':
                score_data['positive_factors'].append("Low risk AutoCheck score")
                score_data['score'] += 10
            elif risk_level == 'high':
                score_data['violations'].append("High risk AutoCheck score")
                score_data['score'] -= 20
            
        except Exception as e:
            logger.error(f"History analysis evaluation failed: {e}")
        
        return score_data
    
    def _calculate_overall_score(self, detailed_scores: Dict[str, Dict[str, Any]]) -> float:
        """Calculate weighted overall score"""
        try:
            # Weights for different categories
            weights = {
                'specifications': 0.15,
                'obd2': 0.25,
                'dashboard': 0.20,
                'image_analysis': 0.15,
                'market_analysis': 0.15,
                'history': 0.10
            }
            
            weighted_score = 0
            total_weight = 0
            
            for category, weight in weights.items():
                if category in detailed_scores:
                    score = detailed_scores[category].get('score', 0)
                    weighted_score += score * weight
                    total_weight += weight
            
            if total_weight > 0:
                return weighted_score / total_weight
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Overall score calculation failed: {e}")
            return 0
    
    def _determine_recommendation(self, evaluation: Dict[str, Any]) -> str:
        """Determine overall recommendation"""
        try:
            overall_score = evaluation['overall_score']
            
            # Check for critical violations
            all_violations = []
            for category_scores in evaluation['detailed_scores'].values():
                all_violations.extend(category_scores.get('violations', []))
            
            # Critical violation keywords
            critical_keywords = [
                'transmission', 'critical', 'major engine', 'major electrical',
                'headlight warning', 'safety system'
            ]
            
            has_critical_violations = any(
                any(keyword in violation.lower() for keyword in critical_keywords)
                for violation in all_violations
            )
            
            if has_critical_violations:
                return 'avoid'
            elif overall_score >= 85:
                return 'strong_buy'
            elif overall_score >= 70:
                return 'buy'
            elif overall_score >= 55:
                return 'consider'
            elif overall_score >= 40:
                return 'caution'
            else:
                return 'avoid'
                
        except Exception as e:
            logger.error(f"Recommendation determination failed: {e}")
            return 'unknown'
    
    def _generate_bid_recommendation(self, vehicle_data: Dict[str, Any], evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate specific bid recommendation"""
        bid_rec = {
            'should_bid': False,
            'max_bid': 0,
            'confidence': 'low',
            'reasoning': []
        }
        
        try:
            recommendation = evaluation['recommendation']
            current_bid = vehicle_data.get('current_bid', 0)
            
            # Market analysis for bid calculation
            dealerslink_analysis = vehicle_data.get('dealerslink_analysis', {})
            trade_margin = dealerslink_analysis.get('trade_margin', 0)
            
            cargurus_analysis = vehicle_data.get('cargurus_analysis', {})
            market_stats = cargurus_analysis.get('market_stats', {})
            avg_market_price = market_stats.get('average_price', current_bid)
            
            if recommendation in ['strong_buy', 'buy']:
                bid_rec['should_bid'] = True
                bid_rec['confidence'] = 'high' if recommendation == 'strong_buy' else 'medium'
                
                # Calculate max bid based on market data
                if trade_margin > 0:
                    # Use trade margin for calculation
                    bid_rec['max_bid'] = current_bid + min(trade_margin * 0.7, 2000)
                else:
                    # Use market price as reference
                    bid_rec['max_bid'] = min(avg_market_price * 0.85, current_bid + 1500)
                
                bid_rec['reasoning'].append(f"Good candidate with score {evaluation['overall_score']:.1f}")
                
            elif recommendation == 'consider':
                bid_rec['should_bid'] = True
                bid_rec['confidence'] = 'low'
                bid_rec['max_bid'] = current_bid + 500  # Conservative bid
                bid_rec['reasoning'].append("Marginal candidate - bid conservatively")
                
            else:
                bid_rec['should_bid'] = False
                bid_rec['reasoning'].append(f"Not recommended: {recommendation}")
            
            # Add specific reasoning from violations
            all_violations = []
            for category_scores in evaluation['detailed_scores'].values():
                all_violations.extend(category_scores.get('violations', []))
            
            if all_violations:
                bid_rec['reasoning'].extend(all_violations[:3])  # Top 3 concerns
            
        except Exception as e:
            logger.error(f"Bid recommendation generation failed: {e}")
        
        return bid_rec
    
    def filter_vehicle_list(self, vehicles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and rank a list of vehicles"""
        try:
            evaluated_vehicles = []
            
            for vehicle in vehicles:
                evaluation = self.evaluate_vehicle(vehicle)
                vehicle['evaluation'] = evaluation
                evaluated_vehicles.append(vehicle)
            
            # Filter out vehicles that don't meet criteria
            recommended_vehicles = [
                v for v in evaluated_vehicles 
                if v['evaluation']['recommendation'] in ['strong_buy', 'buy', 'consider']
            ]
            
            # Sort by overall score (descending)
            recommended_vehicles.sort(
                key=lambda v: v['evaluation']['overall_score'], 
                reverse=True
            )
            
            logger.info(f"Filtered {len(vehicles)} vehicles to {len(recommended_vehicles)} recommendations")
            
            return recommended_vehicles
            
        except Exception as e:
            logger.error(f"Vehicle list filtering failed: {e}")
            return []
