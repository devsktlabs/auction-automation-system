
#!/usr/bin/env python3
"""
CarMax/Manheim Auction Automation System
Main orchestration script for the complete auction data extraction and analysis pipeline
"""

import asyncio
import json
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import sys

# Import all system components
from scrapers.carmax import CarMaxScraper
from scrapers.manheim import ManheimScraper
from integrations.carfax import CarfaxIntegrator
from integrations.autocheck import AutoCheckIntegrator
from integrations.dealerslink import DealersLinkIntegrator
from integrations.cargurus import CarGurusIntegrator
from ai.image_analysis import VehicleImageAnalyzer
from ai.obd2_analysis import OBD2Analyzer
from ai.dashboard_lights import DashboardLightAnalyzer
from ai.filtering import VehicleFilteringEngine
from utils.config import config
from utils.logger import logger
from utils.errors import *

class AuctionAutomationOrchestrator:
    """Main orchestrator for the auction automation system"""
    
    def __init__(self):
        self.carmax_scraper = None
        self.manheim_scraper = None
        self.integrations = {}
        self.ai_analyzers = {}
        self.filtering_engine = VehicleFilteringEngine()
        self.results = []
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            logger.info("Initializing auction automation system...")
            
            # Initialize integrations
            if config.get_integration_config('carfax').get('enabled', True):
                self.integrations['carfax'] = CarfaxIntegrator()
            
            if config.get_integration_config('autocheck').get('enabled', True):
                self.integrations['autocheck'] = AutoCheckIntegrator()
            
            if config.get_integration_config('dealerslink').get('enabled', True):
                self.integrations['dealerslink'] = DealersLinkIntegrator()
            
            if config.get_integration_config('cargurus').get('enabled', True):
                self.integrations['cargurus'] = CarGurusIntegrator()
            
            # Initialize AI analyzers
            if config.get('ai.image_analysis.enabled', True):
                self.ai_analyzers['image'] = VehicleImageAnalyzer()
            
            if config.get('ai.obd2_analysis.enabled', True):
                self.ai_analyzers['obd2'] = OBD2Analyzer()
            
            if config.get('ai.dashboard_analysis.enabled', True):
                self.ai_analyzers['dashboard'] = DashboardLightAnalyzer()
            
            logger.info("System components initialized successfully")
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise ConfigurationError(f"System initialization failed: {e}")
    
    def run_full_pipeline(self, platforms: List[str] = None, search_criteria: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the complete auction automation pipeline"""
        try:
            logger.info("Starting full auction automation pipeline")
            
            platforms = platforms or ['carmax', 'manheim']
            search_criteria = search_criteria or self._get_default_search_criteria()
            
            pipeline_results = {
                'start_time': datetime.now().isoformat(),
                'platforms': platforms,
                'search_criteria': search_criteria,
                'vehicles_found': 0,
                'vehicles_analyzed': 0,
                'recommended_vehicles': 0,
                'results': [],
                'summary': {},
                'errors': []
            }
            
            # Step 1: Vehicle Discovery
            logger.info("Step 1: Discovering vehicles from auction platforms")
            all_vehicles = self._discover_vehicles(platforms, search_criteria)
            pipeline_results['vehicles_found'] = len(all_vehicles)
            
            if not all_vehicles:
                logger.warning("No vehicles found matching criteria")
                return pipeline_results
            
            # Step 2: Comprehensive Analysis
            logger.info(f"Step 2: Analyzing {len(all_vehicles)} vehicles")
            analyzed_vehicles = self._analyze_vehicles(all_vehicles)
            pipeline_results['vehicles_analyzed'] = len(analyzed_vehicles)
            
            # Step 3: Intelligent Filtering
            logger.info("Step 3: Applying intelligent filtering")
            recommended_vehicles = self.filtering_engine.filter_vehicle_list(analyzed_vehicles)
            pipeline_results['recommended_vehicles'] = len(recommended_vehicles)
            pipeline_results['results'] = recommended_vehicles
            
            # Step 4: Generate Summary
            pipeline_results['summary'] = self._generate_pipeline_summary(recommended_vehicles)
            
            # Step 5: Save Results
            self._save_results(pipeline_results)
            
            pipeline_results['end_time'] = datetime.now().isoformat()
            logger.info("Full pipeline completed successfully")
            
            return pipeline_results
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            pipeline_results['errors'].append(str(e))
            return pipeline_results
    
    def _get_default_search_criteria(self) -> Dict[str, Any]:
        """Get default search criteria from configuration"""
        return {
            'year_min': config.get('filtering.year_range.min', 2015),
            'year_max': datetime.now().year,
            'price_max': config.get('filtering.price_range.max', 50000),
            'mileage_max': config.get('filtering.mileage_range.max', 150000)
        }
    
    def _discover_vehicles(self, platforms: List[str], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover vehicles from specified platforms"""
        all_vehicles = []
        
        try:
            for platform in platforms:
                logger.info(f"Searching {platform} platform")
                
                if platform == 'carmax':
                    vehicles = self._search_carmax(criteria)
                elif platform == 'manheim':
                    vehicles = self._search_manheim(criteria)
                else:
                    logger.warning(f"Unknown platform: {platform}")
                    continue
                
                logger.info(f"Found {len(vehicles)} vehicles on {platform}")
                all_vehicles.extend(vehicles)
            
        except Exception as e:
            logger.error(f"Vehicle discovery failed: {e}")
        
        return all_vehicles
    
    def _search_carmax(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search CarMax platform"""
        vehicles = []
        
        try:
            # Initialize CarMax scraper
            self.carmax_scraper = CarMaxScraper()
            
            # Check if login is needed
            if not self.carmax_scraper.initialize():
                logger.warning("CarMax login required - manual intervention needed")
                return vehicles
            
            # Search for vehicles
            vehicle_urls = self.carmax_scraper.search_vehicles(criteria)
            
            # Scrape vehicle details
            for url in vehicle_urls:
                try:
                    vehicle_data = self.carmax_scraper.scrape_vehicle_details(url)
                    if vehicle_data:
                        vehicle_dict = {
                            'platform': 'carmax',
                            'vin': vehicle_data.vin,
                            'year': vehicle_data.year,
                            'make': vehicle_data.make,
                            'model': vehicle_data.model,
                            'trim': vehicle_data.trim,
                            'mileage': vehicle_data.mileage,
                            'current_bid': vehicle_data.current_bid,
                            'buy_now_price': vehicle_data.buy_now_price,
                            'time_left': vehicle_data.time_left,
                            'condition_grade': vehicle_data.condition_grade,
                            'location': vehicle_data.location,
                            'images': vehicle_data.images,
                            'obd2_codes': vehicle_data.obd2_codes,
                            'dashboard_lights': vehicle_data.dashboard_lights,
                            'source_url': vehicle_data.carmax_url
                        }
                        vehicles.append(vehicle_dict)
                        
                except Exception as e:
                    logger.error(f"Failed to scrape CarMax vehicle {url}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"CarMax search failed: {e}")
        finally:
            if self.carmax_scraper:
                self.carmax_scraper.close()
        
        return vehicles
    
    def _search_manheim(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search Manheim platform"""
        vehicles = []
        
        try:
            # Initialize Manheim scraper
            self.manheim_scraper = ManheimScraper()
            
            # Check if login is needed
            if not self.manheim_scraper.initialize():
                logger.warning("Manheim login required - manual intervention needed")
                return vehicles
            
            # Search for vehicles
            vehicle_urls = self.manheim_scraper.search_vehicles(criteria)
            
            # Scrape vehicle details
            for url in vehicle_urls:
                try:
                    vehicle_data = self.manheim_scraper.scrape_vehicle_details(url)
                    if vehicle_data:
                        vehicle_dict = {
                            'platform': 'manheim',
                            'vin': vehicle_data.vin,
                            'year': vehicle_data.year,
                            'make': vehicle_data.make,
                            'model': vehicle_data.model,
                            'trim': vehicle_data.trim,
                            'mileage': vehicle_data.mileage,
                            'current_bid': vehicle_data.current_bid,
                            'reserve_price': vehicle_data.reserve_price,
                            'mmr_value': vehicle_data.mmr_value,
                            'time_left': vehicle_data.time_left,
                            'condition_report': vehicle_data.condition_report,
                            'location': vehicle_data.location,
                            'images': vehicle_data.images,
                            'source_url': vehicle_data.manheim_url
                        }
                        vehicles.append(vehicle_dict)
                        
                except Exception as e:
                    logger.error(f"Failed to scrape Manheim vehicle {url}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Manheim search failed: {e}")
        finally:
            if self.manheim_scraper:
                self.manheim_scraper.close()
        
        return vehicles
    
    def _analyze_vehicles(self, vehicles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform comprehensive analysis on all vehicles"""
        analyzed_vehicles = []
        
        for i, vehicle in enumerate(vehicles):
            try:
                logger.info(f"Analyzing vehicle {i+1}/{len(vehicles)}: {vehicle.get('vin', 'Unknown VIN')}")
                
                # Perform all analyses
                analyzed_vehicle = self._analyze_single_vehicle(vehicle)
                analyzed_vehicles.append(analyzed_vehicle)
                
            except Exception as e:
                logger.error(f"Vehicle analysis failed for {vehicle.get('vin', 'Unknown')}: {e}")
                # Add vehicle with error status
                vehicle['analysis_error'] = str(e)
                analyzed_vehicles.append(vehicle)
        
        return analyzed_vehicles
    
    def _analyze_single_vehicle(self, vehicle: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive analysis on a single vehicle"""
        try:
            vin = vehicle.get('vin')
            
            # Vehicle history analysis
            if 'carfax' in self.integrations:
                logger.debug(f"Getting Carfax history for {vin}")
                carfax_data = self.integrations['carfax'].get_vehicle_history(vin)
                if carfax_data:
                    vehicle['carfax_history'] = carfax_data
                    vehicle['carfax_analysis'] = self.integrations['carfax'].analyze_history_flags(carfax_data)
            
            if 'autocheck' in self.integrations:
                logger.debug(f"Getting AutoCheck history for {vin}")
                autocheck_data = self.integrations['autocheck'].get_vehicle_history(vin)
                if autocheck_data:
                    vehicle['autocheck_history'] = autocheck_data
                    vehicle['autocheck_analysis'] = self.integrations['autocheck'].analyze_autocheck_score(autocheck_data)
            
            # Market analysis
            if 'cargurus' in self.integrations:
                logger.debug(f"Getting CarGurus market analysis for {vin}")
                cargurus_data = self.integrations['cargurus'].search_by_vin(vin)
                if cargurus_data:
                    vehicle['cargurus_data'] = cargurus_data
                    vehicle['cargurus_analysis'] = self.integrations['cargurus'].analyze_market_position(
                        vehicle, vehicle.get('current_bid', 0)
                    )
            
            if 'dealerslink' in self.integrations:
                logger.debug(f"Getting DealersLink appraisal for {vin}")
                dealerslink_data = self.integrations['dealerslink'].get_vehicle_appraisal(vin)
                if dealerslink_data:
                    vehicle['dealerslink_data'] = dealerslink_data
                    vehicle['dealerslink_analysis'] = self.integrations['dealerslink'].analyze_deal_potential(
                        vehicle, vehicle.get('current_bid', 0)
                    )
            
            # AI-powered analysis
            if 'image' in self.ai_analyzers and vehicle.get('images'):
                logger.debug(f"Analyzing images for {vin}")
                vehicle['image_analysis'] = self.ai_analyzers['image'].analyze_vehicle_images(vehicle['images'])
            
            if 'obd2' in self.ai_analyzers and vehicle.get('obd2_codes'):
                logger.debug(f"Analyzing OBD2 codes for {vin}")
                vehicle['obd2_analysis'] = self.ai_analyzers['obd2'].analyze_obd2_codes(vehicle['obd2_codes'])
            
            if 'dashboard' in self.ai_analyzers and vehicle.get('dashboard_lights'):
                logger.debug(f"Analyzing dashboard lights for {vin}")
                vehicle['dashboard_analysis'] = self.ai_analyzers['dashboard'].analyze_dashboard_lights(vehicle['dashboard_lights'])
            
            # Add analysis timestamp
            vehicle['analysis_timestamp'] = datetime.now().isoformat()
            
            return vehicle
            
        except Exception as e:
            logger.error(f"Single vehicle analysis failed: {e}")
            vehicle['analysis_error'] = str(e)
            return vehicle
    
    def _generate_pipeline_summary(self, vehicles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of pipeline results"""
        summary = {
            'total_vehicles': len(vehicles),
            'recommendations': {
                'strong_buy': 0,
                'buy': 0,
                'consider': 0,
                'caution': 0,
                'avoid': 0
            },
            'top_recommendations': [],
            'common_issues': {},
            'market_insights': {}
        }
        
        try:
            # Count recommendations
            for vehicle in vehicles:
                evaluation = vehicle.get('evaluation', {})
                recommendation = evaluation.get('recommendation', 'unknown')
                if recommendation in summary['recommendations']:
                    summary['recommendations'][recommendation] += 1
            
            # Get top 5 recommendations
            top_vehicles = sorted(
                vehicles,
                key=lambda v: v.get('evaluation', {}).get('overall_score', 0),
                reverse=True
            )[:5]
            
            summary['top_recommendations'] = [
                {
                    'vin': v.get('vin'),
                    'year': v.get('year'),
                    'make': v.get('make'),
                    'model': v.get('model'),
                    'current_bid': v.get('current_bid'),
                    'overall_score': v.get('evaluation', {}).get('overall_score', 0),
                    'recommendation': v.get('evaluation', {}).get('recommendation'),
                    'platform': v.get('platform')
                }
                for v in top_vehicles
            ]
            
            # Analyze common issues
            all_violations = []
            for vehicle in vehicles:
                evaluation = vehicle.get('evaluation', {})
                for category_scores in evaluation.get('detailed_scores', {}).values():
                    all_violations.extend(category_scores.get('violations', []))
            
            # Count violation types
            violation_counts = {}
            for violation in all_violations:
                violation_type = violation.split(':')[0].strip()
                violation_counts[violation_type] = violation_counts.get(violation_type, 0) + 1
            
            summary['common_issues'] = dict(sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
        
        return summary
    
    def _save_results(self, results: Dict[str, Any]):
        """Save results to configured storage formats"""
        try:
            storage_config = config.get('storage', {})
            storage_format = storage_config.get('format', 'json')
            local_path = Path(storage_config.get('local_path', './data'))
            
            # Create storage directory
            local_path.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save as JSON
            if storage_format in ['json', 'both']:
                json_file = local_path / f"auction_results_{timestamp}.json"
                with open(json_file, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results saved to {json_file}")
            
            # Save as CSV
            if storage_format in ['csv', 'both']:
                csv_file = local_path / f"auction_results_{timestamp}.csv"
                self._save_csv_results(results, csv_file)
                logger.info(f"Results saved to {csv_file}")
            
            # Save summary report
            summary_file = local_path / f"auction_summary_{timestamp}.txt"
            self._save_summary_report(results, summary_file)
            logger.info(f"Summary saved to {summary_file}")
            
        except Exception as e:
            logger.error(f"Results saving failed: {e}")
    
    def _save_csv_results(self, results: Dict[str, Any], csv_file: Path):
        """Save results in CSV format"""
        try:
            vehicles = results.get('results', [])
            
            if not vehicles:
                return
            
            # Define CSV columns
            columns = [
                'vin', 'platform', 'year', 'make', 'model', 'trim', 'mileage',
                'current_bid', 'overall_score', 'recommendation', 'should_bid',
                'max_bid', 'confidence', 'location', 'source_url'
            ]
            
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                
                for vehicle in vehicles:
                    evaluation = vehicle.get('evaluation', {})
                    bid_rec = evaluation.get('bid_recommendation', {})
                    
                    row = {
                        'vin': vehicle.get('vin', ''),
                        'platform': vehicle.get('platform', ''),
                        'year': vehicle.get('year', ''),
                        'make': vehicle.get('make', ''),
                        'model': vehicle.get('model', ''),
                        'trim': vehicle.get('trim', ''),
                        'mileage': vehicle.get('mileage', ''),
                        'current_bid': vehicle.get('current_bid', ''),
                        'overall_score': evaluation.get('overall_score', ''),
                        'recommendation': evaluation.get('recommendation', ''),
                        'should_bid': bid_rec.get('should_bid', ''),
                        'max_bid': bid_rec.get('max_bid', ''),
                        'confidence': bid_rec.get('confidence', ''),
                        'location': vehicle.get('location', ''),
                        'source_url': vehicle.get('source_url', '')
                    }
                    writer.writerow(row)
                    
        except Exception as e:
            logger.error(f"CSV saving failed: {e}")
    
    def _save_summary_report(self, results: Dict[str, Any], summary_file: Path):
        """Save human-readable summary report"""
        try:
            summary = results.get('summary', {})
            
            with open(summary_file, 'w') as f:
                f.write("AUCTION AUTOMATION SYSTEM - SUMMARY REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Analysis Date: {results.get('start_time', 'Unknown')}\n")
                f.write(f"Platforms Searched: {', '.join(results.get('platforms', []))}\n")
                f.write(f"Vehicles Found: {results.get('vehicles_found', 0)}\n")
                f.write(f"Vehicles Analyzed: {results.get('vehicles_analyzed', 0)}\n")
                f.write(f"Recommended Vehicles: {results.get('recommended_vehicles', 0)}\n\n")
                
                # Recommendation breakdown
                f.write("RECOMMENDATION BREAKDOWN:\n")
                f.write("-" * 25 + "\n")
                recommendations = summary.get('recommendations', {})
                for rec_type, count in recommendations.items():
                    f.write(f"{rec_type.replace('_', ' ').title()}: {count}\n")
                f.write("\n")
                
                # Top recommendations
                f.write("TOP RECOMMENDATIONS:\n")
                f.write("-" * 20 + "\n")
                top_recs = summary.get('top_recommendations', [])
                for i, vehicle in enumerate(top_recs, 1):
                    f.write(f"{i}. {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')}\n")
                    f.write(f"   VIN: {vehicle.get('vin')}\n")
                    f.write(f"   Current Bid: ${vehicle.get('current_bid', 0):,}\n")
                    f.write(f"   Score: {vehicle.get('overall_score', 0):.1f}\n")
                    f.write(f"   Platform: {vehicle.get('platform', '').title()}\n\n")
                
                # Common issues
                f.write("COMMON ISSUES FOUND:\n")
                f.write("-" * 20 + "\n")
                common_issues = summary.get('common_issues', {})
                for issue, count in common_issues.items():
                    f.write(f"{issue}: {count} vehicles\n")
                
        except Exception as e:
            logger.error(f"Summary report saving failed: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            # Close scrapers
            if self.carmax_scraper:
                self.carmax_scraper.close()
            if self.manheim_scraper:
                self.manheim_scraper.close()
            
            # Close integrations
            for integration in self.integrations.values():
                if hasattr(integration, 'close'):
                    integration.close()
            
            logger.info("System cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='CarMax/Manheim Auction Automation System')
    parser.add_argument('--platforms', nargs='+', choices=['carmax', 'manheim'], 
                       default=['carmax', 'manheim'], help='Platforms to search')
    parser.add_argument('--max-price', type=int, help='Maximum bid price')
    parser.add_argument('--max-mileage', type=int, help='Maximum mileage')
    parser.add_argument('--min-year', type=int, help='Minimum year')
    parser.add_argument('--config', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Build search criteria from arguments
    search_criteria = {}
    if args.max_price:
        search_criteria['price_max'] = args.max_price
    if args.max_mileage:
        search_criteria['mileage_max'] = args.max_mileage
    if args.min_year:
        search_criteria['year_min'] = args.min_year
    
    orchestrator = None
    
    try:
        logger.info("Starting Auction Automation System")
        
        # Initialize orchestrator
        orchestrator = AuctionAutomationOrchestrator()
        
        # Run pipeline
        results = orchestrator.run_full_pipeline(
            platforms=args.platforms,
            search_criteria=search_criteria if search_criteria else None
        )
        
        # Print summary
        print("\n" + "="*60)
        print("AUCTION AUTOMATION SYSTEM - RESULTS SUMMARY")
        print("="*60)
        print(f"Vehicles Found: {results['vehicles_found']}")
        print(f"Vehicles Analyzed: {results['vehicles_analyzed']}")
        print(f"Recommended Vehicles: {results['recommended_vehicles']}")
        
        if results['recommended_vehicles'] > 0:
            print(f"\nTop Recommendation:")
            top_vehicle = results['summary']['top_recommendations'][0]
            print(f"  {top_vehicle['year']} {top_vehicle['make']} {top_vehicle['model']}")
            print(f"  VIN: {top_vehicle['vin']}")
            print(f"  Current Bid: ${top_vehicle['current_bid']:,}")
            print(f"  Score: {top_vehicle['overall_score']:.1f}")
        
        print(f"\nResults saved to: ./data/")
        print("="*60)
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)
    finally:
        if orchestrator:
            orchestrator.cleanup()

if __name__ == "__main__":
    main()
