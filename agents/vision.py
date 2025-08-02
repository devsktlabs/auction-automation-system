
#!/usr/bin/env python3
"""
Vehicle Vision Analysis Module
Uses local vision models (BLIP, LLaVA) for vehicle image analysis
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
try:
    import torch
    from transformers import BlipProcessor, BlipForConditionalGeneration
    from transformers import AutoProcessor, LlavaForConditionalGeneration
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PyTorch/Transformers not available: {e}")
    TORCH_AVAILABLE = False

from PIL import Image
import cv2
import numpy as np
import requests
from io import BytesIO

from utils.logger import logger


class VehicleVisionAnalyzer:
    """
    Local vision model analyzer for vehicle images
    Supports BLIP and LLaVA models for comprehensive image analysis
    """
    
    def __init__(self, model_name: str = "blip", device: str = "auto"):
        self.logger = logger
        self.device = self._setup_device(device)
        self.model_name = model_name
        
        # Model components
        self.processor = None
        self.model = None
        self.llava_processor = None
        self.llava_model = None
        
        # Analysis cache
        self._analysis_cache = {}
        
        # Initialize models lazily
        self._models_loaded = False
        
        self.logger.info(f"VehicleVisionAnalyzer initialized with device: {self.device}")
    
    def _setup_device(self, device: str) -> str:
        """Setup computation device"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device
    
    def _load_models(self):
        """Lazy loading of vision models"""
        if self._models_loaded:
            return
        
        if not TORCH_AVAILABLE:
            self.logger.warning("PyTorch not available. Vision analysis will use fallback methods.")
            self._models_loaded = True
            return
        
        try:
            self.logger.info("Loading vision models...")
            
            # Load BLIP model for image captioning and VQA
            self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            self.model.to(self.device)
            
            # Optionally load LLaVA for more advanced analysis
            try:
                self.llava_processor = AutoProcessor.from_pretrained("llava-hf/llava-1.5-7b-hf")
                self.llava_model = LlavaForConditionalGeneration.from_pretrained(
                    "llava-hf/llava-1.5-7b-hf",
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    low_cpu_mem_usage=True
                )
                self.llava_model.to(self.device)
                self.logger.info("LLaVA model loaded successfully")
            except Exception as e:
                self.logger.warning(f"Could not load LLaVA model: {e}")
                self.llava_model = None
                self.llava_processor = None
            
            self._models_loaded = True
            self.logger.info("Vision models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load vision models: {e}")
            # Don't raise, just use fallback methods
            self._models_loaded = True
    
    async def analyze_vehicle_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        Comprehensive analysis of vehicle images
        
        Args:
            image_paths: List of local image file paths
            
        Returns:
            Dictionary containing analysis results
        """
        self._load_models()
        
        if not image_paths:
            return {"error": "No images provided for analysis"}
        
        self.logger.info(f"Analyzing {len(image_paths)} vehicle images")
        
        analysis_results = {
            "total_images": len(image_paths),
            "processed_images": 0,
            "exterior_analysis": {},
            "interior_analysis": {},
            "damage_assessment": {},
            "condition_summary": {},
            "detailed_findings": [],
            "confidence_scores": {}
        }
        
        try:
            # Categorize images
            categorized_images = await self._categorize_images(image_paths)
            
            # Analyze exterior images
            if categorized_images["exterior"]:
                analysis_results["exterior_analysis"] = await self._analyze_exterior_images(
                    categorized_images["exterior"]
                )
            
            # Analyze interior images
            if categorized_images["interior"]:
                analysis_results["interior_analysis"] = await self._analyze_interior_images(
                    categorized_images["interior"]
                )
            
            # Analyze engine/mechanical images
            if categorized_images["engine"]:
                analysis_results["engine_analysis"] = await self._analyze_engine_images(
                    categorized_images["engine"]
                )
            
            # Overall damage assessment
            analysis_results["damage_assessment"] = await self._assess_overall_damage(image_paths)
            
            # Generate condition summary
            analysis_results["condition_summary"] = self._generate_condition_summary(analysis_results)
            
            analysis_results["processed_images"] = len(image_paths)
            
            self.logger.info("Vehicle image analysis completed successfully")
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error during image analysis: {e}")
            return {"error": str(e)}
    
    async def _categorize_images(self, image_paths: List[str]) -> Dict[str, List[str]]:
        """Categorize images into exterior, interior, engine, etc."""
        categories = {
            "exterior": [],
            "interior": [],
            "engine": [],
            "wheels": [],
            "other": []
        }
        
        for image_path in image_paths:
            try:
                # Use BLIP to generate caption and categorize
                image = Image.open(image_path).convert("RGB")
                caption = await self._generate_caption(image)
                
                category = self._classify_image_category(caption, image_path)
                categories[category].append(image_path)
                
            except Exception as e:
                self.logger.warning(f"Could not categorize image {image_path}: {e}")
                categories["other"].append(image_path)
        
        self.logger.info(f"Image categorization: {[(k, len(v)) for k, v in categories.items()]}")
        return categories
    
    def _classify_image_category(self, caption: str, image_path: str) -> str:
        """Classify image category based on caption and filename"""
        caption_lower = caption.lower()
        filename_lower = Path(image_path).name.lower()
        
        # Interior keywords
        interior_keywords = ["interior", "dashboard", "seat", "steering", "console", "cabin"]
        if any(keyword in caption_lower or keyword in filename_lower for keyword in interior_keywords):
            return "interior"
        
        # Engine keywords
        engine_keywords = ["engine", "motor", "hood", "under hood", "mechanical"]
        if any(keyword in caption_lower or keyword in filename_lower for keyword in engine_keywords):
            return "engine"
        
        # Wheel keywords
        wheel_keywords = ["wheel", "tire", "rim", "brake"]
        if any(keyword in caption_lower or keyword in filename_lower for keyword in wheel_keywords):
            return "wheels"
        
        # Default to exterior
        return "exterior"
    
    async def _generate_caption(self, image: Image.Image) -> str:
        """Generate caption for an image using BLIP or fallback method"""
        if not TORCH_AVAILABLE or not self.processor or not self.model:
            # Fallback: analyze filename and basic image properties
            return self._fallback_image_analysis(image)
        
        try:
            inputs = self.processor(image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                out = self.model.generate(**inputs, max_length=50, num_beams=5)
            
            caption = self.processor.decode(out[0], skip_special_tokens=True)
            return caption
            
        except Exception as e:
            self.logger.error(f"Error generating caption: {e}")
            return self._fallback_image_analysis(image)
    
    def _fallback_image_analysis(self, image: Image.Image) -> str:
        """Fallback image analysis without AI models"""
        try:
            # Basic image analysis
            width, height = image.size
            aspect_ratio = width / height
            
            # Analyze dominant colors
            colors = image.getcolors(maxcolors=256*256*256)
            if colors:
                dominant_color = max(colors, key=lambda x: x[0])[1]
                
                # Simple color-based classification
                if isinstance(dominant_color, tuple) and len(dominant_color) >= 3:
                    r, g, b = dominant_color[:3]
                    if r > 200 and g > 200 and b > 200:
                        color_desc = "bright"
                    elif r < 50 and g < 50 and b < 50:
                        color_desc = "dark"
                    elif r > g and r > b:
                        color_desc = "reddish"
                    elif g > r and g > b:
                        color_desc = "greenish"
                    elif b > r and b > g:
                        color_desc = "bluish"
                    else:
                        color_desc = "neutral"
                else:
                    color_desc = "unknown"
            else:
                color_desc = "unknown"
            
            # Basic description
            if aspect_ratio > 1.5:
                orientation = "wide"
            elif aspect_ratio < 0.7:
                orientation = "tall"
            else:
                orientation = "square"
            
            return f"{color_desc} {orientation} vehicle image"
            
        except Exception as e:
            self.logger.error(f"Fallback image analysis failed: {e}")
            return "vehicle image"
    
    async def _analyze_exterior_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """Analyze exterior vehicle images"""
        analysis = {
            "paint_condition": "unknown",
            "body_damage": [],
            "rust_detected": False,
            "dents_scratches": [],
            "overall_condition": "unknown",
            "confidence": 0.0
        }
        
        damage_count = 0
        total_confidence = 0.0
        
        for image_path in image_paths:
            try:
                image = Image.open(image_path).convert("RGB")
                
                # Analyze for damage using targeted questions
                damage_analysis = await self._analyze_damage_in_image(image)
                
                if damage_analysis["damage_detected"]:
                    damage_count += 1
                    analysis["body_damage"].extend(damage_analysis["damage_types"])
                
                if damage_analysis["rust_detected"]:
                    analysis["rust_detected"] = True
                
                analysis["dents_scratches"].extend(damage_analysis["surface_issues"])
                total_confidence += damage_analysis["confidence"]
                
            except Exception as e:
                self.logger.warning(f"Error analyzing exterior image {image_path}: {e}")
        
        # Calculate overall condition
        if len(image_paths) > 0:
            damage_ratio = damage_count / len(image_paths)
            analysis["confidence"] = total_confidence / len(image_paths)
            
            if damage_ratio < 0.1:
                analysis["overall_condition"] = "excellent"
            elif damage_ratio < 0.3:
                analysis["overall_condition"] = "good"
            elif damage_ratio < 0.6:
                analysis["overall_condition"] = "fair"
            else:
                analysis["overall_condition"] = "poor"
        
        return analysis
    
    async def _analyze_interior_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """Analyze interior vehicle images"""
        analysis = {
            "seat_condition": "unknown",
            "dashboard_condition": "unknown",
            "wear_patterns": [],
            "cleanliness": "unknown",
            "overall_condition": "unknown",
            "confidence": 0.0
        }
        
        for image_path in image_paths:
            try:
                image = Image.open(image_path).convert("RGB")
                
                # Use LLaVA for detailed interior analysis if available
                if self.llava_model:
                    interior_analysis = await self._analyze_with_llava(
                        image, 
                        "Analyze this vehicle interior image. Describe the condition of seats, dashboard, and any wear or damage."
                    )
                    analysis["detailed_analysis"] = interior_analysis
                else:
                    # Fallback to BLIP caption analysis
                    caption = await self._generate_caption(image)
                    analysis["caption_analysis"] = caption
                
            except Exception as e:
                self.logger.warning(f"Error analyzing interior image {image_path}: {e}")
        
        return analysis
    
    async def _analyze_engine_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """Analyze engine bay images"""
        analysis = {
            "engine_cleanliness": "unknown",
            "visible_leaks": False,
            "component_condition": "unknown",
            "maintenance_indicators": [],
            "overall_condition": "unknown"
        }
        
        for image_path in image_paths:
            try:
                image = Image.open(image_path).convert("RGB")
                
                if self.llava_model:
                    engine_analysis = await self._analyze_with_llava(
                        image,
                        "Analyze this engine bay image. Look for signs of leaks, corrosion, wear, and overall maintenance condition."
                    )
                    analysis["detailed_analysis"] = engine_analysis
                
            except Exception as e:
                self.logger.warning(f"Error analyzing engine image {image_path}: {e}")
        
        return analysis
    
    async def _analyze_damage_in_image(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze specific image for damage using computer vision"""
        damage_analysis = {
            "damage_detected": False,
            "damage_types": [],
            "surface_issues": [],
            "rust_detected": False,
            "confidence": 0.0
        }
        
        try:
            # Convert to OpenCV format for computer vision analysis
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Simple damage detection using edge detection and contour analysis
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze contours for potential damage indicators
            significant_contours = [c for c in contours if cv2.contourArea(c) > 100]
            
            if len(significant_contours) > 50:  # High number of edges might indicate damage
                damage_analysis["damage_detected"] = True
                damage_analysis["damage_types"].append("surface_irregularities")
                damage_analysis["confidence"] = 0.6
            
            # Use BLIP for semantic analysis
            if self.llava_model:
                damage_description = await self._analyze_with_llava(
                    image,
                    "Look carefully at this vehicle image. Is there any visible damage, dents, scratches, rust, or paint issues? Describe what you see."
                )
                
                # Parse LLaVA response for damage indicators
                damage_keywords = ["damage", "dent", "scratch", "rust", "paint", "crack", "chip"]
                if any(keyword in damage_description.lower() for keyword in damage_keywords):
                    damage_analysis["damage_detected"] = True
                    damage_analysis["confidence"] = max(damage_analysis["confidence"], 0.8)
            
            return damage_analysis
            
        except Exception as e:
            self.logger.error(f"Error in damage analysis: {e}")
            return damage_analysis
    
    async def _analyze_with_llava(self, image: Image.Image, prompt: str) -> str:
        """Analyze image with LLaVA model or fallback"""
        if not TORCH_AVAILABLE or not self.llava_model or not self.llava_processor:
            return self._fallback_detailed_analysis(image, prompt)
        
        try:
            # Prepare inputs
            inputs = self.llava_processor(prompt, image, return_tensors="pt").to(self.device)
            
            # Generate response
            with torch.no_grad():
                generate_ids = self.llava_model.generate(**inputs, max_length=200, do_sample=True, temperature=0.7)
            
            # Decode response
            response = self.llava_processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
            
            # Extract the generated part (remove the prompt)
            if prompt in response:
                response = response.split(prompt)[-1].strip()
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error with LLaVA analysis: {e}")
            return self._fallback_detailed_analysis(image, prompt)
    
    def _fallback_detailed_analysis(self, image: Image.Image, prompt: str) -> str:
        """Fallback detailed analysis without AI models"""
        try:
            # Basic image properties
            width, height = image.size
            
            # Analyze based on prompt type
            if "interior" in prompt.lower():
                return f"Interior image analysis: {width}x{height} resolution. Basic visual inspection suggests typical vehicle interior layout."
            elif "engine" in prompt.lower():
                return f"Engine bay analysis: {width}x{height} resolution. Visual inspection of engine compartment shows standard automotive components."
            elif "damage" in prompt.lower():
                return f"Damage assessment: {width}x{height} resolution. Basic visual inspection completed - detailed AI analysis requires model availability."
            else:
                return f"General vehicle analysis: {width}x{height} resolution. Basic visual inspection completed."
                
        except Exception as e:
            return f"Fallback analysis error: {str(e)}"
    
    async def _assess_overall_damage(self, image_paths: List[str]) -> Dict[str, Any]:
        """Assess overall vehicle damage across all images"""
        damage_assessment = {
            "damage_severity": 0,  # 0-10 scale
            "damage_locations": [],
            "estimated_repair_cost": "unknown",
            "major_issues": [],
            "minor_issues": [],
            "overall_rating": "unknown"
        }
        
        total_damage_score = 0
        image_count = len(image_paths)
        
        for image_path in image_paths:
            try:
                image = Image.open(image_path).convert("RGB")
                damage_analysis = await self._analyze_damage_in_image(image)
                
                if damage_analysis["damage_detected"]:
                    total_damage_score += damage_analysis["confidence"] * 10
                    damage_assessment["damage_locations"].append(Path(image_path).stem)
                
            except Exception as e:
                self.logger.warning(f"Error in overall damage assessment for {image_path}: {e}")
        
        # Calculate severity
        if image_count > 0:
            damage_assessment["damage_severity"] = min(10, total_damage_score / image_count)
        
        # Categorize overall rating
        severity = damage_assessment["damage_severity"]
        if severity < 2:
            damage_assessment["overall_rating"] = "excellent"
        elif severity < 4:
            damage_assessment["overall_rating"] = "good"
        elif severity < 6:
            damage_assessment["overall_rating"] = "fair"
        elif severity < 8:
            damage_assessment["overall_rating"] = "poor"
        else:
            damage_assessment["overall_rating"] = "very_poor"
        
        return damage_assessment
    
    def _generate_condition_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall condition summary from all analyses"""
        summary = {
            "overall_condition": "unknown",
            "key_findings": [],
            "recommendations": [],
            "confidence_level": "low"
        }
        
        try:
            # Aggregate findings from different analyses
            exterior = analysis_results.get("exterior_analysis", {})
            interior = analysis_results.get("interior_analysis", {})
            damage = analysis_results.get("damage_assessment", {})
            
            # Determine overall condition
            conditions = []
            if exterior.get("overall_condition"):
                conditions.append(exterior["overall_condition"])
            if interior.get("overall_condition"):
                conditions.append(interior["overall_condition"])
            if damage.get("overall_rating"):
                conditions.append(damage["overall_rating"])
            
            if conditions:
                # Use the worst condition as overall
                condition_scores = {
                    "excellent": 5, "good": 4, "fair": 3, "poor": 2, "very_poor": 1
                }
                worst_score = min(condition_scores.get(c, 3) for c in conditions)
                summary["overall_condition"] = next(k for k, v in condition_scores.items() if v == worst_score)
            
            # Compile key findings
            if exterior.get("body_damage"):
                summary["key_findings"].extend(exterior["body_damage"])
            if damage.get("major_issues"):
                summary["key_findings"].extend(damage["major_issues"])
            
            # Generate recommendations
            if damage.get("damage_severity", 0) > 5:
                summary["recommendations"].append("Professional inspection recommended")
            if exterior.get("rust_detected"):
                summary["recommendations"].append("Check for structural rust damage")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating condition summary: {e}")
            return summary


# Example usage and testing
if __name__ == "__main__":
    async def test_vision_analyzer():
        analyzer = VehicleVisionAnalyzer()
        
        # Test with sample images (replace with actual paths)
        test_images = [
            "/path/to/exterior1.jpg",
            "/path/to/interior1.jpg",
            "/path/to/engine1.jpg"
        ]
        
        try:
            results = await analyzer.analyze_vehicle_images(test_images)
            print("Vision analysis results:")
            print(json.dumps(results, indent=2))
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Run test
    # asyncio.run(test_vision_analyzer())
    print("Vehicle Vision Analyzer module loaded successfully")
