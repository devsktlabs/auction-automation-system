
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import requests
from PIL import Image
import io
import torch
import torchvision.transforms as transforms
from transformers import pipeline
import base64

from utils.config import config
from utils.logger import logger
from utils.errors import ValidationError

class VehicleImageAnalyzer:
    """AI-powered vehicle image analysis for condition assessment"""
    
    def __init__(self):
        self.confidence_threshold = config.get('ai.image_analysis.confidence_threshold', 0.7)
        self.damage_detection_enabled = config.get('ai.image_analysis.damage_detection', True)
        
        # Initialize models
        self.damage_detector = None
        self.condition_classifier = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize AI models for image analysis"""
        try:
            # Initialize damage detection pipeline
            if self.damage_detection_enabled:
                self.damage_detector = pipeline(
                    "object-detection",
                    model="facebook/detr-resnet-50",
                    device=0 if torch.cuda.is_available() else -1
                )
            
            logger.info("Image analysis models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize image analysis models: {e}")
            self.damage_detector = None
    
    def analyze_vehicle_images(self, image_urls: List[str]) -> Dict[str, any]:
        """Analyze all vehicle images and provide comprehensive assessment"""
        analysis_results = {
            'overall_condition': 'unknown',
            'damage_detected': False,
            'condition_score': 0,
            'detailed_analysis': [],
            'recommendations': []
        }
        
        try:
            image_analyses = []
            
            for i, url in enumerate(image_urls):
                logger.info(f"Analyzing image {i+1}/{len(image_urls)}: {url}")
                
                # Download and analyze image
                image_analysis = self._analyze_single_image(url)
                if image_analysis:
                    image_analyses.append(image_analysis)
            
            # Aggregate results
            if image_analyses:
                analysis_results = self._aggregate_image_analyses(image_analyses)
            
        except Exception as e:
            logger.error(f"Vehicle image analysis failed: {e}")
        
        return analysis_results
    
    def _analyze_single_image(self, image_url: str) -> Optional[Dict[str, any]]:
        """Analyze a single vehicle image"""
        try:
            # Download image
            image = self._download_image(image_url)
            if image is None:
                return None
            
            analysis = {
                'image_url': image_url,
                'damage_detected': False,
                'damages': [],
                'condition_indicators': {},
                'image_quality': 'good'
            }
            
            # Damage detection
            if self.damage_detector:
                damages = self._detect_damage(image)
                analysis['damages'] = damages
                analysis['damage_detected'] = len(damages) > 0
            
            # Condition assessment
            condition_indicators = self._assess_condition_indicators(image)
            analysis['condition_indicators'] = condition_indicators
            
            # Image quality check
            quality_score = self._assess_image_quality(image)
            analysis['image_quality'] = self._categorize_quality(quality_score)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Single image analysis failed for {image_url}: {e}")
            return None
    
    def _download_image(self, url: str) -> Optional[np.ndarray]:
        """Download image from URL and convert to OpenCV format"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Convert to PIL Image
            pil_image = Image.open(io.BytesIO(response.content))
            
            # Convert to RGB if necessary
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to OpenCV format
            opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            return opencv_image
            
        except Exception as e:
            logger.error(f"Failed to download image {url}: {e}")
            return None
    
    def _detect_damage(self, image: np.ndarray) -> List[Dict[str, any]]:
        """Detect damage in vehicle image using AI"""
        damages = []
        
        try:
            if not self.damage_detector:
                return damages
            
            # Convert OpenCV image to PIL for the model
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            # Run damage detection
            detections = self.damage_detector(pil_image)
            
            # Filter and categorize detections
            for detection in detections:
                confidence = detection['score']
                label = detection['label']
                
                if confidence >= self.confidence_threshold:
                    # Categorize damage types
                    damage_type = self._categorize_damage(label)
                    
                    if damage_type:
                        damages.append({
                            'type': damage_type,
                            'confidence': confidence,
                            'location': detection['box'],
                            'severity': self._assess_damage_severity(detection)
                        })
            
        except Exception as e:
            logger.error(f"Damage detection failed: {e}")
        
        return damages
    
    def _categorize_damage(self, label: str) -> Optional[str]:
        """Categorize detected objects as damage types"""
        damage_keywords = {
            'scratch': ['scratch', 'scrape', 'mark'],
            'dent': ['dent', 'ding', 'depression'],
            'rust': ['rust', 'corrosion', 'oxidation'],
            'crack': ['crack', 'fracture', 'split'],
            'missing_part': ['missing', 'broken', 'damaged'],
            'paint_damage': ['paint', 'chip', 'fade']
        }
        
        label_lower = label.lower()
        
        for damage_type, keywords in damage_keywords.items():
            if any(keyword in label_lower for keyword in keywords):
                return damage_type
        
        return None
    
    def _assess_damage_severity(self, detection: Dict[str, any]) -> str:
        """Assess damage severity based on detection confidence and size"""
        confidence = detection['score']
        box = detection['box']
        
        # Calculate relative size of damage
        box_area = (box['xmax'] - box['xmin']) * (box['ymax'] - box['ymin'])
        
        if confidence > 0.9 and box_area > 10000:
            return 'severe'
        elif confidence > 0.8 and box_area > 5000:
            return 'moderate'
        elif confidence > 0.7:
            return 'minor'
        else:
            return 'minimal'
    
    def _assess_condition_indicators(self, image: np.ndarray) -> Dict[str, any]:
        """Assess various condition indicators from image"""
        indicators = {}
        
        try:
            # Paint condition assessment
            indicators['paint_condition'] = self._assess_paint_condition(image)
            
            # Body panel alignment
            indicators['panel_alignment'] = self._assess_panel_alignment(image)
            
            # Tire condition (if visible)
            indicators['tire_condition'] = self._assess_tire_condition(image)
            
            # Interior condition (if interior image)
            indicators['interior_condition'] = self._assess_interior_condition(image)
            
        except Exception as e:
            logger.error(f"Condition indicator assessment failed: {e}")
        
        return indicators
    
    def _assess_paint_condition(self, image: np.ndarray) -> Dict[str, any]:
        """Assess paint condition using color analysis"""
        try:
            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Calculate color uniformity
            color_std = np.std(hsv[:, :, 1])  # Saturation standard deviation
            
            # Detect potential fade or discoloration
            brightness_std = np.std(hsv[:, :, 2])  # Value standard deviation
            
            condition_score = 100 - min(color_std + brightness_std, 100)
            
            if condition_score > 80:
                condition = 'excellent'
            elif condition_score > 60:
                condition = 'good'
            elif condition_score > 40:
                condition = 'fair'
            else:
                condition = 'poor'
            
            return {
                'condition': condition,
                'score': condition_score,
                'uniformity': 100 - color_std,
                'brightness_consistency': 100 - brightness_std
            }
            
        except Exception as e:
            logger.error(f"Paint condition assessment failed: {e}")
            return {'condition': 'unknown', 'score': 0}
    
    def _assess_panel_alignment(self, image: np.ndarray) -> Dict[str, any]:
        """Assess body panel alignment using edge detection"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find lines (panel edges)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
            
            alignment_score = 100
            
            if lines is not None:
                # Analyze line parallelism and gaps
                # This is a simplified assessment
                line_angles = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    angle = np.arctan2(y2 - y1, x2 - x1)
                    line_angles.append(angle)
                
                if line_angles:
                    angle_std = np.std(line_angles)
                    alignment_score = max(0, 100 - angle_std * 100)
            
            if alignment_score > 90:
                condition = 'excellent'
            elif alignment_score > 70:
                condition = 'good'
            elif alignment_score > 50:
                condition = 'fair'
            else:
                condition = 'poor'
            
            return {
                'condition': condition,
                'score': alignment_score
            }
            
        except Exception as e:
            logger.error(f"Panel alignment assessment failed: {e}")
            return {'condition': 'unknown', 'score': 0}
    
    def _assess_tire_condition(self, image: np.ndarray) -> Dict[str, any]:
        """Assess tire condition if tires are visible"""
        try:
            # This is a simplified tire assessment
            # In practice, you'd use more sophisticated tire detection
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Look for circular shapes (wheels/tires)
            circles = cv2.HoughCircles(
                gray, cv2.HOUGH_GRADIENT, 1, 20,
                param1=50, param2=30, minRadius=20, maxRadius=200
            )
            
            if circles is not None:
                # Simplified tire condition assessment
                return {
                    'condition': 'visible',
                    'tires_detected': len(circles[0]),
                    'assessment': 'requires_manual_inspection'
                }
            else:
                return {
                    'condition': 'not_visible',
                    'tires_detected': 0
                }
                
        except Exception as e:
            logger.error(f"Tire condition assessment failed: {e}")
            return {'condition': 'unknown'}
    
    def _assess_interior_condition(self, image: np.ndarray) -> Dict[str, any]:
        """Assess interior condition if it's an interior image"""
        try:
            # Simplified interior assessment based on color analysis
            # Check for wear patterns, stains, etc.
            
            # Convert to HSV
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Look for dark spots (potential stains)
            dark_threshold = 50
            dark_pixels = np.sum(hsv[:, :, 2] < dark_threshold)
            total_pixels = hsv.shape[0] * hsv.shape[1]
            dark_ratio = dark_pixels / total_pixels
            
            # Assess based on dark spot ratio
            if dark_ratio < 0.1:
                condition = 'excellent'
                score = 95
            elif dark_ratio < 0.2:
                condition = 'good'
                score = 80
            elif dark_ratio < 0.3:
                condition = 'fair'
                score = 60
            else:
                condition = 'poor'
                score = 40
            
            return {
                'condition': condition,
                'score': score,
                'wear_indicators': dark_ratio
            }
            
        except Exception as e:
            logger.error(f"Interior condition assessment failed: {e}")
            return {'condition': 'unknown', 'score': 0}
    
    def _assess_image_quality(self, image: np.ndarray) -> float:
        """Assess image quality for analysis reliability"""
        try:
            # Calculate image sharpness using Laplacian variance
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Normalize to 0-100 scale
            quality_score = min(laplacian_var / 1000 * 100, 100)
            
            return quality_score
            
        except Exception as e:
            logger.error(f"Image quality assessment failed: {e}")
            return 50.0  # Default medium quality
    
    def _categorize_quality(self, score: float) -> str:
        """Categorize image quality score"""
        if score > 80:
            return 'excellent'
        elif score > 60:
            return 'good'
        elif score > 40:
            return 'fair'
        else:
            return 'poor'
    
    def _aggregate_image_analyses(self, analyses: List[Dict[str, any]]) -> Dict[str, any]:
        """Aggregate multiple image analyses into overall assessment"""
        aggregated = {
            'overall_condition': 'unknown',
            'damage_detected': False,
            'condition_score': 0,
            'detailed_analysis': analyses,
            'recommendations': []
        }
        
        try:
            # Check for any damage
            damage_detected = any(analysis.get('damage_detected', False) for analysis in analyses)
            aggregated['damage_detected'] = damage_detected
            
            # Calculate overall condition score
            condition_scores = []
            
            for analysis in analyses:
                # Weight different condition indicators
                paint_score = analysis.get('condition_indicators', {}).get('paint_condition', {}).get('score', 50)
                panel_score = analysis.get('condition_indicators', {}).get('panel_alignment', {}).get('score', 50)
                
                # Penalize for damage
                damage_penalty = len(analysis.get('damages', [])) * 10
                
                image_score = max(0, (paint_score + panel_score) / 2 - damage_penalty)
                condition_scores.append(image_score)
            
            if condition_scores:
                overall_score = sum(condition_scores) / len(condition_scores)
                aggregated['condition_score'] = overall_score
                
                # Categorize overall condition
                if overall_score > 85:
                    aggregated['overall_condition'] = 'excellent'
                elif overall_score > 70:
                    aggregated['overall_condition'] = 'good'
                elif overall_score > 55:
                    aggregated['overall_condition'] = 'fair'
                else:
                    aggregated['overall_condition'] = 'poor'
            
            # Generate recommendations
            aggregated['recommendations'] = self._generate_recommendations(aggregated, analyses)
            
        except Exception as e:
            logger.error(f"Image analysis aggregation failed: {e}")
        
        return aggregated
    
    def _generate_recommendations(self, aggregated: Dict[str, any], analyses: List[Dict[str, any]]) -> List[str]:
        """Generate recommendations based on image analysis"""
        recommendations = []
        
        try:
            # Damage-based recommendations
            if aggregated['damage_detected']:
                severe_damages = []
                for analysis in analyses:
                    for damage in analysis.get('damages', []):
                        if damage.get('severity') in ['severe', 'moderate']:
                            severe_damages.append(damage['type'])
                
                if severe_damages:
                    recommendations.append(f"Significant damage detected: {', '.join(set(severe_damages))}")
                    recommendations.append("Recommend professional inspection before bidding")
                else:
                    recommendations.append("Minor damage detected - factor into bid price")
            
            # Condition-based recommendations
            condition = aggregated['overall_condition']
            if condition == 'excellent':
                recommendations.append("Excellent visual condition - good candidate for retail")
            elif condition == 'good':
                recommendations.append("Good condition with minor cosmetic issues")
            elif condition == 'fair':
                recommendations.append("Fair condition - budget for reconditioning costs")
            else:
                recommendations.append("Poor condition - high reconditioning costs expected")
            
            # Image quality warnings
            poor_quality_images = sum(1 for analysis in analyses 
                                    if analysis.get('image_quality') == 'poor')
            
            if poor_quality_images > len(analyses) / 2:
                recommendations.append("Warning: Many low-quality images - request additional photos")
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
        
        return recommendations
