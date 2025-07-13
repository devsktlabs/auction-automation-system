
import os
import random
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
try:
    from playwright_stealth import stealth_async
except ImportError:
    # Fallback for different playwright-stealth versions
    try:
        from playwright_stealth import stealth as stealth_async
    except ImportError:
        stealth_async = None
from cryptography.fernet import Fernet
import json
from datetime import datetime, timedelta

from utils.config import config
from utils.logger import logger
from utils.errors import BrowserError, AuthenticationError

class StealthBrowser:
    """Advanced stealth browser with anti-detection capabilities"""
    
    def __init__(self, profile_name: str = "default"):
        self.profile_name = profile_name
        self.driver: Optional[uc.Chrome] = None
        self.profile_path = self._get_profile_path()
        self.encryption_key = self._get_encryption_key()
        
    def _get_profile_path(self) -> Path:
        """Get profile directory path"""
        profiles_dir = Path(config.get('browser.user_data_dir', './profiles'))
        profile_path = profiles_dir / self.profile_name
        profile_path.mkdir(parents=True, exist_ok=True)
        return profile_path
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for session data"""
        key_file = self.profile_path / "session.key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def create_stealth_driver(self) -> uc.Chrome:
        """Create Chrome driver with stealth configuration"""
        options = uc.ChromeOptions()
        
        # Basic stealth options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User data directory for persistent sessions
        options.add_argument(f"--user-data-dir={self.profile_path}")
        
        # Random user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ]
        options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # Headless mode if configured
        if config.get('browser.headless', True):
            options.add_argument("--headless=new")
        
        # Proxy configuration
        if config.get('browser.proxy_enabled', False):
            proxy = self._get_proxy()
            if proxy:
                options.add_argument(f"--proxy-server={proxy}")
        
        try:
            driver = uc.Chrome(options=options, version_main=None)
            
            # Execute stealth scripts
            self._apply_stealth_scripts(driver)
            
            self.driver = driver
            logger.info(f"Created stealth browser with profile: {self.profile_name}")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create stealth driver: {e}")
            raise BrowserError(f"Browser initialization failed: {e}")
    
    def _apply_stealth_scripts(self, driver: uc.Chrome):
        """Apply additional stealth scripts to bypass detection"""
        
        # Remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Spoof plugins
        driver.execute_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        # Spoof languages
        driver.execute_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        # Canvas fingerprint randomization
        driver.execute_script("""
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type) {
                const context = getContext.apply(this, arguments);
                if (type === '2d') {
                    const getImageData = context.getImageData;
                    context.getImageData = function() {
                        const imageData = getImageData.apply(this, arguments);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                        }
                        return imageData;
                    };
                }
                return context;
            };
        """)
    
    def _get_proxy(self) -> Optional[str]:
        """Get proxy from configuration or rotation list"""
        proxies = config.get('browser.residential_proxies', [])
        if proxies:
            return random.choice(proxies)
        return None
    
    def human_like_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add human-like delay between actions"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def human_mouse_movement(self, element):
        """Simulate human-like mouse movement"""
        if not self.driver:
            raise BrowserError("Driver not initialized")
            
        actions = ActionChains(self.driver)
        
        # Get element location and size
        location = element.location
        size = element.size
        
        # Calculate random offset within element
        offset_x = random.randint(-size['width']//4, size['width']//4)
        offset_y = random.randint(-size['height']//4, size['height']//4)
        
        # Move to element with offset
        actions.move_to_element_with_offset(element, offset_x, offset_y)
        
        # Add random pause
        self.human_like_delay(0.5, 1.5)
        
        actions.perform()
    
    def save_session_cookies(self, platform: str):
        """Save encrypted session cookies"""
        if not self.driver:
            return
            
        cookies = self.driver.get_cookies()
        session_data = {
            'cookies': cookies,
            'timestamp': datetime.now().isoformat(),
            'platform': platform,
            'url': self.driver.current_url
        }
        
        # Encrypt session data
        cipher_suite = Fernet(self.encryption_key)
        json_data = json.dumps(session_data)
        encrypted_data = cipher_suite.encrypt(json_data.encode())
        
        # Save to file
        session_file = self.profile_path / f"{platform}_session.enc"
        with open(session_file, 'wb') as f:
            f.write(encrypted_data)
        
        logger.info(f"Saved encrypted session for {platform}")
    
    def load_session_cookies(self, platform: str) -> bool:
        """Load encrypted session cookies"""
        if not self.driver:
            return False
            
        session_file = self.profile_path / f"{platform}_session.enc"
        
        if not session_file.exists():
            logger.info(f"No saved session found for {platform}")
            return False
        
        try:
            # Load and decrypt session data
            with open(session_file, 'rb') as f:
                encrypted_data = f.read()
            
            cipher_suite = Fernet(self.encryption_key)
            json_data = cipher_suite.decrypt(encrypted_data).decode()
            session_data = json.loads(json_data)
            
            # Check if session is still valid (24 hours)
            timestamp = datetime.fromisoformat(session_data['timestamp'])
            if datetime.now() - timestamp > timedelta(hours=24):
                logger.info(f"Session expired for {platform}")
                return False
            
            # Load cookies
            for cookie in session_data['cookies']:
                # Remove problematic keys
                cookie.pop('expiry', None)
                cookie.pop('sameSite', None)
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Failed to add cookie: {e}")
            
            logger.info(f"Loaded session for {platform}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load session for {platform}: {e}")
            return False
    
    def quit(self):
        """Quit browser and cleanup"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None

class PlaywrightStealth:
    """Playwright-based stealth browser for advanced scenarios"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def create_stealth_browser(self):
        """Create Playwright browser with stealth configuration"""
        playwright = await async_playwright().start()
        
        # Launch browser with stealth args
        self.browser = await playwright.chromium.launch(
            headless=config.get('browser.headless', True),
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=self._get_random_user_agent(),
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        # Create page and apply stealth
        self.page = await self.context.new_page()
        if stealth_async:
            await stealth_async(self.page)
        
        return self.browser, self.context, self.page
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent"""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        ]
        return random.choice(agents)
    
    async def close(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()
