
"""Custom exceptions for the auction automation system"""

class AuctionBotError(Exception):
    """Base exception for auction bot errors"""
    pass

class AuthenticationError(AuctionBotError):
    """Raised when authentication fails"""
    pass

class RateLimitError(AuctionBotError):
    """Raised when rate limit is exceeded"""
    pass

class ScrapingError(AuctionBotError):
    """Raised when scraping fails"""
    pass

class DataExtractionError(AuctionBotError):
    """Raised when data extraction fails"""
    pass

class ValidationError(AuctionBotError):
    """Raised when data validation fails"""
    pass

class IntegrationError(AuctionBotError):
    """Raised when external service integration fails"""
    pass

class BrowserError(AuctionBotError):
    """Raised when browser automation fails"""
    pass

class ConfigurationError(AuctionBotError):
    """Raised when configuration is invalid"""
    pass

class StorageError(AuctionBotError):
    """Raised when data storage operations fail"""
    pass
