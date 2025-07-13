
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

class Config:
    """Configuration manager for the auction automation system"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/config.yaml"
        self.base_dir = Path(__file__).parent.parent
        
        # Load environment variables
        load_dotenv(self.base_dir / ".env")
        
        # Load configuration
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = self.base_dir / self.config_path
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        # Replace environment variable placeholders
        return self._replace_env_vars(config)
    
    def _replace_env_vars(self, obj):
        """Recursively replace ${VAR} placeholders with environment variables"""
        if isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            return os.getenv(env_var, obj)
        else:
            return obj
    
    def get(self, key: str, default=None):
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific configuration"""
        return self.get(f'platforms.{platform}', {})
    
    def get_integration_config(self, service: str) -> Dict[str, Any]:
        """Get integration service configuration"""
        return self.get(f'integrations.{service}', {})
    
    def is_test_environment(self) -> bool:
        """Check if running in test environment"""
        return self.get('system.environment') == 'test'

# Global configuration instance
config = Config()
