
from typing import Dict, List, Optional
import re
from utils.config import config
from utils.logger import logger

class OBD2Analyzer:
    """OBD2 diagnostic code analysis and interpretation"""
    
    def __init__(self):
        self.critical_codes = config.get('ai.obd2_analysis.critical_codes', [
            'P0700', 'P0750', 'P0755', 'P0760'  # Transmission codes
        ])
        
        # Load OBD2 code database
        self.code_database = self._load_code_database()
    
    def _load_code_database(self) -> Dict[str, Dict[str, any]]:
        """Load comprehensive OBD2 code database"""
        return {
            # Powertrain codes (P0xxx)
            'P0001': {
                'description': 'Fuel Volume Regulator Control Circuit/Open',
                'system': 'fuel',
                'severity': 'moderate',
                'category': 'emissions'
            },
            'P0030': {
                'description': 'HO2S Heater Control Circuit (Bank 1 Sensor 1)',
                'system': 'emissions',
                'severity': 'minor',
                'category': 'emissions'
            },
            'P0100': {
                'description': 'Mass or Volume Air Flow Circuit Malfunction',
                'system': 'engine',
                'severity': 'moderate',
                'category': 'performance'
            },
            'P0171': {
                'description': 'System Too Lean (Bank 1)',
                'system': 'fuel',
                'severity': 'moderate',
                'category': 'performance'
            },
            'P0300': {
                'description': 'Random/Multiple Cylinder Misfire Detected',
                'system': 'engine',
                'severity': 'severe',
                'category': 'engine'
            },
            'P0420': {
                'description': 'Catalyst System Efficiency Below Threshold (Bank 1)',
                'system': 'emissions',
                'severity': 'moderate',
                'category': 'emissions'
            },
            'P0700': {
                'description': 'Transmission Control System Malfunction',
                'system': 'transmission',
                'severity': 'critical',
                'category': 'transmission'
            },
            'P0750': {
                'description': 'Shift Solenoid A Malfunction',
                'system': 'transmission',
                'severity': 'critical',
                'category': 'transmission'
            },
            'P0755': {
                'description': 'Shift Solenoid B Malfunction',
                'system': 'transmission',
                'severity': 'critical',
                'category': 'transmission'
            },
            'P0760': {
                'description': 'Shift Solenoid C Malfunction',
                'system': 'transmission',
                'severity': 'critical',
                'category': 'transmission'
            },
            
            # Body codes (B0xxx)
            'B0001': {
                'description': 'Driver Airbag Circuit Short to Ground',
                'system': 'safety',
                'severity': 'severe',
                'category': 'safety'
            },
            
            # Chassis codes (C0xxx)
            'C0035': {
                'description': 'Left Front Wheel Speed Circuit Malfunction',
                'system': 'abs',
                'severity': 'moderate',
                'category': 'safety'
            },
            
            # Network codes (U0xxx)
            'U0100': {
                'description': 'Lost Communication with ECM/PCM',
                'system': 'communication',
                'severity': 'severe',
                'category': 'electrical'
            }
        }
    
    def analyze_obd2_codes(self, codes: List[str]) -> Dict[str, any]:
        """Analyze OBD2 codes and provide comprehensive assessment"""
        analysis = {
            'codes_analyzed': len(codes),
            'critical_issues': [],
            'moderate_issues': [],
            'minor_issues': [],
            'system_analysis': {},
            'overall_assessment': 'unknown',
            'inspection_readiness': 'unknown',
            'recommendations': []
        }
        
        try:
            if not codes:
                analysis['overall_assessment'] = 'no_codes'
                analysis['inspection_readiness'] = 'ready'
                analysis['recommendations'].append("No diagnostic codes present - good sign")
                return analysis
            
            # Analyze each code
            for code in codes:
                code_info = self._analyze_single_code(code)
                if code_info:
                    severity = code_info.get('severity', 'unknown')
                    
                    if severity == 'critical':
                        analysis['critical_issues'].append(code_info)
                    elif severity == 'severe' or severity == 'moderate':
                        analysis['moderate_issues'].append(code_info)
                    else:
                        analysis['minor_issues'].append(code_info)
            
            # System-level analysis
            analysis['system_analysis'] = self._analyze_by_system(codes)
            
            # Overall assessment
            analysis['overall_assessment'] = self._determine_overall_assessment(analysis)
            
            # Inspection readiness
            analysis['inspection_readiness'] = self._assess_inspection_readiness(codes)
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_obd2_recommendations(analysis)
            
        except Exception as e:
            logger.error(f"OBD2 analysis failed: {e}")
        
        return analysis
    
    def _analyze_single_code(self, code: str) -> Optional[Dict[str, any]]:
        """Analyze a single OBD2 code"""
        try:
            # Clean and validate code format
            code = code.upper().strip()
            
            if not re.match(r'^[PBCU]\d{4}$', code):
                logger.warning(f"Invalid OBD2 code format: {code}")
                return None
            
            # Get code information from database
            code_info = self.code_database.get(code, {})
            
            if not code_info:
                # Generic analysis for unknown codes
                code_info = self._analyze_unknown_code(code)
            
            # Add the actual code
            code_info['code'] = code
            
            # Determine if critical
            code_info['is_critical'] = code in self.critical_codes
            
            return code_info
            
        except Exception as e:
            logger.error(f"Single code analysis failed for {code}: {e}")
            return None
    
    def _analyze_unknown_code(self, code: str) -> Dict[str, any]:
        """Analyze unknown OBD2 code based on code structure"""
        code_type = code[0]
        code_number = int(code[1:])
        
        # Basic categorization by code type
        if code_type == 'P':
            system = 'powertrain'
            if 0 <= code_number <= 99:
                category = 'fuel_air'
            elif 100 <= code_number <= 199:
                category = 'fuel_air'
            elif 200 <= code_number <= 299:
                category = 'fuel_injection'
            elif 300 <= code_number <= 399:
                category = 'ignition'
            elif 400 <= code_number <= 499:
                category = 'emissions'
            elif 500 <= code_number <= 599:
                category = 'speed_idle'
            elif 600 <= code_number <= 699:
                category = 'computer'
            elif 700 <= code_number <= 799:
                category = 'transmission'
            else:
                category = 'other'
        elif code_type == 'B':
            system = 'body'
            category = 'body_systems'
        elif code_type == 'C':
            system = 'chassis'
            category = 'chassis_systems'
        elif code_type == 'U':
            system = 'network'
            category = 'communication'
        else:
            system = 'unknown'
            category = 'unknown'
        
        return {
            'description': f'Unknown {system} code',
            'system': system,
            'severity': 'moderate',  # Default to moderate for unknown codes
            'category': category
        }
    
    def _analyze_by_system(self, codes: List[str]) -> Dict[str, any]:
        """Analyze codes grouped by vehicle system"""
        system_analysis = {}
        
        try:
            # Group codes by system
            systems = {}
            for code in codes:
                code_info = self._analyze_single_code(code)
                if code_info:
                    system = code_info.get('system', 'unknown')
                    if system not in systems:
                        systems[system] = []
                    systems[system].append(code_info)
            
            # Analyze each system
            for system, system_codes in systems.items():
                severities = [code.get('severity', 'unknown') for code in system_codes]
                
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
                    'code_count': len(system_codes),
                    'health_status': system_health,
                    'codes': [code['code'] for code in system_codes],
                    'primary_concerns': [code['description'] for code in system_codes 
                                       if code.get('severity') in ['critical', 'severe']]
                }
            
        except Exception as e:
            logger.error(f"System analysis failed: {e}")
        
        return system_analysis
    
    def _determine_overall_assessment(self, analysis: Dict[str, any]) -> str:
        """Determine overall vehicle assessment based on OBD2 codes"""
        try:
            critical_count = len(analysis['critical_issues'])
            moderate_count = len(analysis['moderate_issues'])
            minor_count = len(analysis['minor_issues'])
            
            if critical_count > 0:
                return 'critical_issues'
            elif moderate_count > 3:
                return 'multiple_moderate_issues'
            elif moderate_count > 0:
                return 'moderate_issues'
            elif minor_count > 5:
                return 'multiple_minor_issues'
            elif minor_count > 0:
                return 'minor_issues'
            else:
                return 'no_significant_issues'
                
        except Exception as e:
            logger.error(f"Overall assessment determination failed: {e}")
            return 'unknown'
    
    def _assess_inspection_readiness(self, codes: List[str]) -> str:
        """Assess if vehicle is ready for emissions inspection"""
        try:
            # Check for emissions-related codes
            emissions_codes = []
            for code in codes:
                code_info = self._analyze_single_code(code)
                if code_info and code_info.get('category') == 'emissions':
                    emissions_codes.append(code)
            
            if not codes:
                return 'ready'
            elif emissions_codes:
                return 'not_ready_emissions'
            elif any(code in self.critical_codes for code in codes):
                return 'not_ready_critical'
            else:
                return 'ready_with_codes'
                
        except Exception as e:
            logger.error(f"Inspection readiness assessment failed: {e}")
            return 'unknown'
    
    def _generate_obd2_recommendations(self, analysis: Dict[str, any]) -> List[str]:
        """Generate recommendations based on OBD2 analysis"""
        recommendations = []
        
        try:
            # Critical issues
            if analysis['critical_issues']:
                recommendations.append("CRITICAL: Major system failures detected - avoid purchase")
                for issue in analysis['critical_issues']:
                    recommendations.append(f"Critical: {issue['description']}")
            
            # Transmission issues (user's specific concern)
            transmission_issues = analysis['system_analysis'].get('transmission', {})
            if transmission_issues:
                recommendations.append("WARNING: Transmission codes detected - high repair risk")
                recommendations.append("User criteria: Avoid vehicles with transmission issues")
            
            # Moderate issues
            if analysis['moderate_issues']:
                recommendations.append(f"Moderate issues detected ({len(analysis['moderate_issues'])} codes)")
                recommendations.append("Factor repair costs into bid price")
            
            # Inspection readiness
            readiness = analysis['inspection_readiness']
            if readiness == 'not_ready_emissions':
                recommendations.append("Vehicle will not pass emissions inspection")
            elif readiness == 'not_ready_critical':
                recommendations.append("Critical codes prevent inspection passage")
            
            # System-specific recommendations
            system_analysis = analysis['system_analysis']
            
            if 'engine' in system_analysis:
                engine_health = system_analysis['engine']['health_status']
                if engine_health in ['critical', 'severe']:
                    recommendations.append("Engine system issues - major repair risk")
            
            if 'safety' in system_analysis:
                recommendations.append("Safety system codes detected - immediate attention required")
            
            # Positive indicators
            if analysis['overall_assessment'] == 'no_significant_issues':
                recommendations.append("OBD2 analysis shows no significant issues")
            elif analysis['overall_assessment'] == 'minor_issues':
                recommendations.append("Only minor issues detected - good candidate")
            
        except Exception as e:
            logger.error(f"OBD2 recommendation generation failed: {e}")
        
        return recommendations
    
    def check_user_criteria_compliance(self, codes: List[str]) -> Dict[str, any]:
        """Check if vehicle meets user's specific OBD2 criteria"""
        compliance = {
            'meets_criteria': True,
            'violations': [],
            'concerns': []
        }
        
        try:
            # Check for transmission issues (user's avoid criteria)
            transmission_codes = []
            for code in codes:
                code_info = self._analyze_single_code(code)
                if code_info and code_info.get('system') == 'transmission':
                    transmission_codes.append(code)
            
            if transmission_codes:
                compliance['meets_criteria'] = False
                compliance['violations'].append("Transmission codes detected")
                compliance['concerns'].extend([
                    f"Transmission code: {code}" for code in transmission_codes
                ])
            
            # Check for major electrical issues
            electrical_codes = []
            for code in codes:
                code_info = self._analyze_single_code(code)
                if (code_info and 
                    code_info.get('category') == 'electrical' and 
                    code_info.get('severity') in ['critical', 'severe']):
                    electrical_codes.append(code)
            
            if electrical_codes:
                compliance['meets_criteria'] = False
                compliance['violations'].append("Major electrical issues detected")
            
            # Check for major engine issues
            engine_codes = []
            for code in codes:
                code_info = self._analyze_single_code(code)
                if (code_info and 
                    code_info.get('system') == 'engine' and 
                    code_info.get('severity') in ['critical', 'severe']):
                    engine_codes.append(code)
            
            if engine_codes:
                compliance['meets_criteria'] = False
                compliance['violations'].append("Major engine issues detected")
            
            # OBD2 readiness check (user prefers OBD2 ready vehicles)
            readiness = self._assess_inspection_readiness(codes)
            if readiness not in ['ready', 'ready_with_codes']:
                compliance['concerns'].append("Vehicle not OBD2 inspection ready")
            
        except Exception as e:
            logger.error(f"User criteria compliance check failed: {e}")
        
        return compliance
