
import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from utils.logger import logger

@dataclass
class RateLimitConfig:
    requests_per_minute: int
    burst_limit: int
    cooldown_seconds: int

class RateLimiter:
    """Advanced rate limiter with burst protection and adaptive delays"""
    
    def __init__(self):
        self.request_history: Dict[str, list] = {}
        self.last_request: Dict[str, datetime] = {}
        self.consecutive_requests: Dict[str, int] = {}
        
    def can_make_request(self, service: str, config: RateLimitConfig) -> bool:
        """Check if request can be made without violating rate limits"""
        now = datetime.now()
        
        # Initialize service tracking
        if service not in self.request_history:
            self.request_history[service] = []
            self.consecutive_requests[service] = 0
        
        # Clean old requests (older than 1 minute)
        cutoff = now - timedelta(minutes=1)
        self.request_history[service] = [
            req_time for req_time in self.request_history[service] 
            if req_time > cutoff
        ]
        
        # Check rate limit
        if len(self.request_history[service]) >= config.requests_per_minute:
            return False
        
        # Check burst limit
        if self.consecutive_requests[service] >= config.burst_limit:
            last_req = self.last_request.get(service)
            if last_req and (now - last_req).seconds < config.cooldown_seconds:
                return False
            else:
                # Reset burst counter after cooldown
                self.consecutive_requests[service] = 0
        
        return True
    
    def record_request(self, service: str):
        """Record a request for rate limiting"""
        now = datetime.now()
        
        if service not in self.request_history:
            self.request_history[service] = []
            self.consecutive_requests[service] = 0
        
        self.request_history[service].append(now)
        self.last_request[service] = now
        self.consecutive_requests[service] += 1
        
        logger.debug(f"Recorded request for {service}. Total in last minute: {len(self.request_history[service])}")
    
    def wait_if_needed(self, service: str, config: RateLimitConfig):
        """Wait if necessary to respect rate limits"""
        while not self.can_make_request(service, config):
            wait_time = self._calculate_wait_time(service, config)
            logger.info(f"Rate limit reached for {service}. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
    
    async def async_wait_if_needed(self, service: str, config: RateLimitConfig):
        """Async version of wait_if_needed"""
        while not self.can_make_request(service, config):
            wait_time = self._calculate_wait_time(service, config)
            logger.info(f"Rate limit reached for {service}. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
    
    def _calculate_wait_time(self, service: str, config: RateLimitConfig) -> float:
        """Calculate optimal wait time"""
        now = datetime.now()
        
        # If we hit burst limit, wait for cooldown
        if self.consecutive_requests.get(service, 0) >= config.burst_limit:
            last_req = self.last_request.get(service)
            if last_req:
                elapsed = (now - last_req).seconds
                return max(0, config.cooldown_seconds - elapsed)
        
        # Otherwise, wait until oldest request in window expires
        if self.request_history.get(service):
            oldest_request = min(self.request_history[service])
            wait_until = oldest_request + timedelta(minutes=1)
            wait_seconds = (wait_until - now).total_seconds()
            return max(1, wait_seconds)
        
        return 1

# Global rate limiter instance
rate_limiter = RateLimiter()
