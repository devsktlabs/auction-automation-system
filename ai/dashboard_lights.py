
from typing import List, Dict, Optional
import re
from utils.config import config
from utils.logger import logger

class DashboardLightAnalyzer:
    """Dashboard warning light analysis and interpretation"""
    
    def __init__(self):
        self.warning_lights = config.get('ai.dashboard_analysis.warning_lights', [
            'check_engine', 'transmission', 'abs', 'airbag'
        ])
        
        # Load dashboard light database
        self.light_database = self._load_light_database()
    
    def _load_light_database(self) -> Dict[str, Dict[str, any]]:
        """Load comprehensive dashboard warning light database"""
        return {
            # Engine and Powertrain
            'check_engine': {
                'name': 'Check Engine Light',
                'system': 'engine',
                'severity': 'moderate',
                'category': 'powertrain',
                'description': 'Engine management system has detected a problem',
                'immediate_concern': False,
                'inspection_impact': True
            },
            'oil_pressure': {
                'name': 'Oil Pressure Warning',
                'system': 'engine',
                'severity': 'critical',
                'category': 'powertrain',
                'description': 'Low engine oil pressure detected',
                'immediate_concern': True,
                'inspection_impact': False
            },
            'coolant_temperature': {
                'name': 'Engine Temperature Warning',
                'system': 'cooling',
                'severity': 'severe',
                'category': 'powertrain',
                'description': 'Engine overheating detected',
                'immediate_concern': True,
                'inspection_impact': False
            },
            
            # Transmission
            'transmission': {
                'name': 'Transmission Warning',
                'system': 'transmission',
                'severity': 'severe',
                'category': 'powertrain',
                'description': 'Transmission system malfunction',
                'immediate_concern': False,
                'inspection_impact': False
            },
            'transmission_temperature': {
                'name': 'Transmission Temperature',
                'system': 'transmission',
                'severity': 'moderate',
                'category': 'powertrain',
                'description': 'Transmission overheating',
                'immediate_concern': False,
                'inspection_impact': False
            },
            
            # Braking System
            'abs': {
                'name': 'ABS Warning Light',
                'system': 'brakes',
                'severity': 'moderate',
                'category': 'safety',
                'description': 'Anti-lock braking system malfunction',
                'immediate_concern': False,
                'inspection_impact': True
            },
            'brake_system': {
                'name': 'Brake System Warning',
                'system': 'brakes',
                'severity': 'critical',
                'category': 'safety',
                'description': 'Brake system malfunction or low brake fluid',
                'immediate_concern': True,
                'inspection_impact': True
            },
            'parking_brake': {
                'name': 'Parking Brake Engaged',
                'system': 'brakes',
                'severity': 'minor',
                'category': 'normal',
                'description': 'Parking brake is engaged',
                'immediate_concern': False,
                'inspection_impact': False
            },
            
            # Safety Systems
            'airbag': {
                'name': 'Airbag System Warning',
                'system': 'safety',
                'severity': 'severe',
                'category': 'safety',
                'description': 'Airbag system malfunction',
                'immediate_concern': False,
                'inspection_impact': True
            },
            'seatbelt': {
                'name': 'Seatbelt Warning',
                'system': 'safety',
                'severity': 'minor',
                'category': 'normal',
                'description': 'Seatbelt not fastened',
                'immediate_concern': False,
                'inspection_impact': False
            },
            
            # Electrical System
            'battery': {
                'name': 'Battery/Charging System',
                'system': 'electrical',
                'severity': 'moderate',
                'category': 'electrical',
                'description': 'Charging system malfunction',
                'immediate_concern': False,
                'inspection_impact': False
            },
            'alternator': {
                'name': 'Alternator Warning',
                'system': 'electrical',
                'severity': 'moderate',
                'category': 'electrical',
                'description': 'Alternator not charging properly',
                'immediate_concern': False,
                'inspection_impact': False
            },
            
            # Lighting
            'headlight_out': {
                'name': 'Headlight Out',
                'system': 'lighting',
                'severity': 'moderate',
                'category': 'lighting',
                'description': 'Headlight bulb failure',
                'immediate_concern': False,
                'inspection_impact': True
            },
            'taillight_out': {
                'name': 'Taillight Out',
                'system': 'lighting',
                'severity': 'minor',
                'category': 'lighting',
                'description': 'Taillight bulb failure',
                'immediate_concern': False,
                'inspection_impact': True
            },
            
            # Fuel System
            'low_fuel': {
                'name': 'Low Fuel Warning',
                'system': 'fuel',
                'severity': 'minor',
                'category': 'normal',
                'description': 'Fuel level is low',
                'immediate_concern': False,
                'inspection_impact': False
            },
            'fuel_system': {
                'name': 'Fuel System Warning',
                'system': 'fuel',
                'severity': 'moderate',
                'category': 'powertrain',
                'description': 'Fuel system malfunction',
                'immediate_concern': False,
                'inspection_impact': True
            },
            
            # Steering and Suspension
            'power_steering': {
                'name': 'Power Steering Warning',
                'system': 'steering',
                'severity': 'moderate',
                'category': 'handling',
                'description': 'Power steering system malfunction',
                'immediate_concern': False,
                'inspection_impact': False
            },
            'suspension': {
                'name': 'Suspension Warning',
                'system': 'suspension',
                'severity': 'moderate',
                'category': 'handling',
                'description': 'Suspension system issue',
                'immediate_concern': False,
                'inspection_impact': False
            },
            
            # TPMS
            'tire_pressure': {
                'name': 'Tire Pressure Monitoring',
                'system': 'tires',
                'severity': 'minor',
                'category': 'maintenance',
                'description': 'Tire pressure low or TPMS malfunction',
                'immediate_concern': False,
                'inspection_impact': False
            }
        }
    
    def analyze_dashboard_lights(self, lights: List[str]) -> Dict[str, any]:
        """Analyze dashboard warning lights and provide assessment"""
        analysis = {
            'lights_analyzed': len(lights),
            'critical_warnings': [],
            'severe_warnings': [],
            'moderate_warnings': [],
            'minor_warnings': [],
            'system_analysis': {},
            'overall_assessment': 'unknown',
            'safety_concerns': [],
            'inspection_impact': False,
            'recommendations': []
        }
        
        try:
            if not lights:
                analysis['overall_assessment'] = 'no_warnings'
                analysis['recommendations'].append("No dashboard warning lights - good sign")
                return analysis
            
            # Analyze each light
            for light in lights:
                light_info = self._analyze_single_light(light)
                if light_info:
                    severity = light_info.get('severity', 'unknown')
                    
                    if severity == 'critical':
                        analysis['critical_warnings'].append(light_info)
                    elif severity == 'severe':
                        analysis['severe_warnings'].append(light_info)
                    elif severity == 'moderate':
                        analysis['moderate_warnings'].append(light_info)
                    else:
                        analysis['minor_warnings'].append(light_info)
                    
                    # Check for safety concerns
                    if light_info.get('category') == 'safety':
                        analysis['safety_concerns'].append(light_info)
                    
                    # Check inspection impact
                    if light_info.get('inspection_impact'):
                        analysis['inspection_impact'] = True
            
            # System-level analysis
            analysis['system_analysis'] = self._analyze_by_system(lights)
            
            # Overall assessment
            analysis['overall_assessment'] = self._determine_overall_assessment(analysis)
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_dashboard_recommendations(analysis)
            
        except Exception as e:
            logger.error(f"Dashboard light analysis failed: {e}")
        
        return analysis
    
    def _analyze_single_light(self, light: str) -> Optional[Dict[str, any]]:
        """Analyze a single dashboard warning light"""
        try:
            # Normalize light name
            light_normalized = self._normalize_light_name(light)
            
            # Get light information from database
            light_info = self.light_database.get(light_normalized, {})
            
            if not light_info:
                # Try to categorize unknown light
                light_info = self._analyze_unknown_light(light)
            
            # Add the original light name
            light_info['original_name'] = light
            light_info['normalized_name'] = light_normalized
            
            return light_info
            
        except Exception as e:
            logger.error(f"Single light analysis failed for {light}: {e}")
            return None
    
    def _normalize_light_name(self, light: str) -> str:
        """Normalize dashboard light name for database lookup"""
        # Convert to lowercase and remove special characters
        normalized = re.sub(r'[^a-z0-9_]', '_', light.lower().strip())
        
        # Common variations mapping
        variations = {
            'engine_light': 'check_engine',
            'cel': 'check_engine',
            'mil': 'check_engine',
            'service_engine': 'check_engine',
            'abs_light': 'abs',
            'anti_lock': 'abs',
            'airbag_light': 'airbag',
            'srs': 'airbag',
            'brake_light': 'brake_system',
            'oil_light': 'oil_pressure',
            'temp_light': 'coolant_temperature',
            'battery_light': 'battery',
            'charge_light': 'battery',
            'tpms': 'tire_pressure',
            'tire_light': 'tire_pressure'
        }
        
        return variations.get(normalized, normalized)
    
    def _analyze_unknown_light(self, light: str) -> Dict[str, any]:
        """Analyze unknown dashboard light based on name patterns"""
        light_lower = light.lower()
        
        # Pattern-based categorization
        if any(keyword in light_lower for keyword in ['engine', 'check', 'mil', 'cel']):
            return {
                'name': 'Unknown Engine Warning',
                'system': 'engine',
                'severity': 'moderate',
                'category': 'powertrain',
                'description': f'Unknown engine-related warning: {light}',
                'immediate_concern': False,
                'inspection_impact': True
            }
        elif any(keyword in light_lower for keyword in ['brake', 'abs']):
            return {
                'name': 'Unknown Brake Warning',
                'system': 'brakes',
                'severity': 'severe',
                'category': 'safety',
                'description': f'Unknown brake-related warning: {light}',
                'immediate_concern': True,
                'inspection_impact': True
            }
        elif any(keyword in light_lower for keyword in ['airbag', 'srs', 'safety']):
            return {
                'name': 'Unknown Safety Warning',
                'system': 'safety',
                'severity': 'severe',
                'category': 'safety',
                'description': f'Unknown safety system warning: {light}',
                'immediate_concern': False,
                'inspection_impact': True
            }
        elif any(keyword in light_lower for keyword in ['transmission', 'trans']):
            return {
                'name': 'Unknown Transmission Warning',
                'system': 'transmission',
                'severity': 'severe',
                'category': 'powertrain',
                'description': f'Unknown transmission warning: {light}',
                'immediate_concern': False,
                'inspection_impact': False
            }
        else:
            return {
                'name': 'Unknown Warning Light',
                'system': 'unknown',
                'severity': 'moderate',
                'category': 'unknown',
                'description': f'Unknown warning light: {light}',
                'immediate_concern': False,
                'inspection_impact': True
            }
    
    def _analyze_by_system(self, lights: List[str]) -> Dict[str, any]:
        """Analyze lights grouped by vehicle system"""
        system_analysis = {}
        
        try:
            # Group lights by system
            systems = {}
            for light in lights:
                light_info = self._analyze_single_light(light)
                if light_info:
                    system = light_info.get('system', 'unknown')
                    if system not in systems:
                        systems[system] = []
                    systems[system].append(light_info)
            
            # Analyze each system
            for system, system_lights in systems.items():
                severities = [light.get('severity', 'unknown') for light in system_lights]
                immediate_concerns = any(light.get('immediate_concern', False) for light in system_lights)
                
                # Determine system health
                if 'critical' in severities:
                    system_health = 'critical'
                elif 'severe' in severities:
                    system_health = 'severe'
                elif 'moderate' in severities:
                    system_health = 'moderate'
                else:
                    system_health = 'minor'
                
                system_analysis[system] = {
                    'light_count': len(system_lights),
                    'health_status': system_health,
                    'immediate_concern': immediate_concerns,
                    'lights': [light['original_name'] for light in system_lights],
                    'primary_concerns': [light['description'] for light in system_lights 
                                       if light.get('severity') in ['critical', 'severe']]
                }
            
        except Exception as e:
            logger.error(f"System analysis failed: {e}")
        
        return system_analysis
    
    def _determine_overall_assessment(self, analysis: Dict[str, any]) -> str:
        """Determine overall assessment based on dashboard lights"""
        try:
            critical_count = len(analysis['critical_warnings'])
            severe_count = len(analysis['severe_warnings'])
            moderate_count = len(analysis['moderate_warnings'])
            safety_concerns = len(analysis['safety_concerns'])
            
            if critical_count > 0:
                return 'critical_warnings'
            elif severe_count > 0 or safety_concerns > 0:
                return 'severe_warnings'
            elif moderate_count > 2:
                return 'multiple_moderate_warnings'
            elif moderate_count > 0:
                return 'moderate_warnings'
            else:
                return 'minor_warnings_only'
                
        except Exception as e:
            logger.error(f"Overall assessment determination failed: {e}")
            return 'unknown'
    
    def _generate_dashboard_recommendations(self, analysis: Dict[str, any]) -> List[str]:
        """Generate recommendations based on dashboard light analysis"""
        recommendations = []
        
        try:
            # Critical warnings
            if analysis['critical_warnings']:
                recommendations.append("CRITICAL: Immediate safety concerns detected")
                for warning in analysis['critical_warnings']:
                    recommendations.append(f"Critical: {warning['description']}")
            
            # Safety concerns
            if analysis['safety_concerns']:
                recommendations.append("Safety system warnings detected - high priority")
                for concern in analysis['safety_concerns']:
                    recommendations.append(f"Safety: {concern['description']}")
            
            # Headlight concerns (user's specific criteria)
            headlight_issues = []
            for warning in (analysis['moderate_warnings'] + analysis['minor_warnings']):
                if warning.get('system') == 'lighting' and 'headlight' in warning.get('name', '').lower():
                    headlight_issues.append(warning)
            
            if headlight_issues:
                recommendations.append("WARNING: Headlight issues detected")
                recommendations.append("User criteria: Ensure headlights work properly")
            
            # Transmission warnings (user's avoid criteria)
            transmission_warnings = analysis['system_analysis'].get('transmission', {})
            if transmission_warnings:
                recommendations.append("WARNING: Transmission warning lights detected")
                recommendations.append("User criteria: Avoid vehicles with transmission issues")
            
            # Engine warnings
            engine_warnings = analysis['system_analysis'].get('engine', {})
            if engine_warnings:
                engine_health = engine_warnings['health_status']
                if engine_health in ['critical', 'severe']:
                    recommendations.append("Major engine warnings - high repair risk")
                else:
                    recommendations.append("Engine warning detected - investigate further")
            
            # Inspection impact
            if analysis['inspection_impact']:
                recommendations.append("Warning lights will affect vehicle inspection")
            
            # System-specific recommendations
            system_analysis = analysis['system_analysis']
            
            if 'brakes' in system_analysis:
                brake_health = system_analysis['brakes']['health_status']
                if brake_health in ['critical', 'severe']:
                    recommendations.append("Brake system warnings - safety critical")
            
            if 'electrical' in system_analysis:
                recommendations.append("Electrical system warnings - check charging system")
            
            # Positive indicators
            if analysis['overall_assessment'] == 'no_warnings':
                recommendations.append("No dashboard warnings - excellent sign")
            elif analysis['overall_assessment'] == 'minor_warnings_only':
                recommendations.append("Only minor warnings - generally acceptable")
            
        except Exception as e:
            logger.error(f"Dashboard recommendation generation failed: {e}")
        
        return recommendations
    
    def check_user_criteria_compliance(self, lights: List[str]) -> Dict[str, any]:
        """Check if vehicle meets user's dashboard light criteria"""
        compliance = {
            'meets_criteria': True,
            'violations': [],
            'concerns': []
        }
        
        try:
            # Check for headlight issues (user requires working headlights)
            headlight_issues = []
            for light in lights:
                light_info = self._analyze_single_light(light)
                if (light_info and 
                    light_info.get('system') == 'lighting' and 
                    'headlight' in light_info.get('name', '').lower()):
                    headlight_issues.append(light)
            
            if headlight_issues:
                compliance['meets_criteria'] = False
                compliance['violations'].append("Headlight warning lights detected")
                compliance['concerns'].extend([
                    f"Headlight issue: {light}" for light in headlight_issues
                ])
            
            # Check for transmission warnings (user avoids transmission issues)
            transmission_warnings = []
            for light in lights:
                light_info = self._analyze_single_light(light)
                if light_info and light_info.get('system') == 'transmission':
                    transmission_warnings.append(light)
            
            if transmission_warnings:
                compliance['meets_criteria'] = False
                compliance['violations'].append("Transmission warning lights detected")
            
            # Check for major electrical issues
            electrical_warnings = []
            for light in lights:
                light_info = self._analyze_single_light(light)
                if (light_info and 
                    light_info.get('system') == 'electrical' and 
                    light_info.get('severity') in ['critical', 'severe']):
                    electrical_warnings.append(light)
            
            if electrical_warnings:
                compliance['meets_criteria'] = False
                compliance['violations'].append("Major electrical warning lights detected")
            
            # Check for major engine issues
            engine_warnings = []
            for light in lights:
                light_info = self._analyze_single_light(light)
                if (light_info and 
                    light_info.get('system') == 'engine' and 
                    light_info.get('severity') in ['critical', 'severe']):
                    engine_warnings.append(light)
            
            if engine_warnings:
                compliance['meets_criteria'] = False
                compliance['violations'].append("Major engine warning lights detected")
            
        except Exception as e:
            logger.error(f"User criteria compliance check failed: {e}")
        
        return compliance
