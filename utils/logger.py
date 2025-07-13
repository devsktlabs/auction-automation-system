
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from rich.console import Console
from rich.logging import RichHandler
from utils.config import config

class AuctionLogger:
    """Enhanced logging system for auction automation"""
    
    def __init__(self):
        self.console = Console()
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with file and console handlers"""
        logger = logging.getLogger("auction_bot")
        logger.setLevel(getattr(logging, config.get('logging.level', 'INFO')))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler with rotation
        log_file = Path(config.get('logging.file_path', './logs/auction_bot.log'))
        log_file.parent.mkdir(exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self._parse_size(config.get('logging.max_file_size', '10MB')),
            backupCount=config.get('logging.backup_count', 5)
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Rich console handler
        console_handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=True,
            markup=True
        )
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        size_str = size_str.upper()
        if size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        else:
            return int(size_str)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)
    
    def log_vehicle_processing(self, vin: str, platform: str, status: str):
        """Log vehicle processing status"""
        self.info(f"Vehicle {vin} on {platform}: {status}")
    
    def log_error_with_context(self, error: Exception, context: dict):
        """Log error with additional context"""
        self.error(f"Error: {str(error)}", extra=context)

# Global logger instance
logger = AuctionLogger()
