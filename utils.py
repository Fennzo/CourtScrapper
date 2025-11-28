"""
Utility functions for the scraper
"""
import time
import logging
import subprocess
import requests
import threading
import socket
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from config import CHROME_PATH

logger = logging.getLogger(__name__)

# Chrome startup polling configuration
CHROME_STARTUP_TIMEOUT = 10.0  # Maximum time (seconds) to wait for Chrome debug endpoint
CHROME_STARTUP_POLL_INTERVAL = 0.2  # Interval (seconds) between polling attempts

# Thread-safe caching for Chrome user agent (cache once per process)
ua_cache = None
ua_lock = threading.Lock()

# Configure both console and file logging for the current scraper session.
# Uses single log file with thread identification for multi-threaded environments.
# Professional approach: Single log file allows chronological event correlation across threads.
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Enhanced format includes thread name and module name for multi-threaded debugging
    # Format: timestamp - thread_name - module - level - message
    log_format = '%(asctime)s - [%(threadName)s] - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Ensure the results folder exists and return its pathlib handle.
def create_output_dir():
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)
    return output_dir

# Poll Chrome debug endpoint until it responds or timeout is reached
# Args:
#     debug_port: The port number Chrome is running on
#     timeout: Maximum time (seconds) to wait for endpoint to respond
#     poll_interval: Time (seconds) to wait between polling attempts
# Returns:
#     None if successful, raises TimeoutError if timeout is reached
# Raises:
#     TimeoutError: If the endpoint doesn't respond within the timeout period
def wait_for_chrome_debug_endpoint(debug_port, timeout=CHROME_STARTUP_TIMEOUT, poll_interval=CHROME_STARTUP_POLL_INTERVAL):
    """
    Polls the Chrome debug endpoint until it responds or timeout is reached.
    Uses short backoff intervals between attempts and handles connection exceptions.
    """
    endpoint_url = f"http://localhost:{debug_port}/json/version"
    start_time = time.time()
    attempt = 0
    
    while True:
        elapsed = time.time() - start_time
        
        # Check if timeout has been reached
        if elapsed >= timeout:
            raise TimeoutError(
                f"Chrome debug endpoint did not respond within {timeout} seconds. "
                f"Endpoint: {endpoint_url}"
            )
        
        # Attempt to connect to the debug endpoint
        try:
            response = requests.get(endpoint_url, timeout=min(poll_interval * 2, 2.0))
            response.raise_for_status()
            # Endpoint is ready
            logger.debug(f"Chrome debug endpoint ready after {elapsed:.2f}s ({attempt} attempts)")
            return
        except requests.exceptions.ConnectionError:
            # Endpoint not ready yet, continue polling
            attempt += 1
            time.sleep(poll_interval)
        except requests.exceptions.Timeout:
            # Request timeout, but endpoint might still be starting, continue polling
            attempt += 1
            time.sleep(poll_interval)
        except requests.RequestException as e:
            # Other request errors - log but continue polling in case it's transient
            logger.debug(f"Request error while polling Chrome endpoint (attempt {attempt}): {e}")
            attempt += 1
            time.sleep(poll_interval)

# Extract real Chrome user agent from system Chrome browser
# Thread-safe: caches UA once per process, uses lock to prevent concurrent extraction
def get_chrome_user_agent():
    global ua_cache
    
    # Return cached UA if available
    if ua_cache is not None:
        return ua_cache
    
    # Use lock to ensure only one thread extracts UA
    with ua_lock:
        # Double-check after acquiring lock (another thread might have set it)
        if ua_cache is not None:
            return ua_cache
        
        chrome_path = CHROME_PATH
        temp_dir = None
        proc = None
        debug_port = None
        temp_socket = None
        
        try:
            # Let OS assign an available port instead of pre-checking 9222
            # Keep the socket open until Chrome successfully binds to prevent TOCTOU race condition
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                temp_socket.bind(('', 0))
                debug_port = temp_socket.getsockname()[1]
                # Do NOT close socket here - keep it open to prevent port from being claimed by another process
                logger.debug(f"OS assigned debug port: {debug_port} (socket held open)")
            except Exception as e:
                if temp_socket:
                    temp_socket.close()
                logger.error(f"Failed to get OS-assigned port: {e}")
                raise RuntimeError(f"Unable to obtain a free port for Chrome debugging: {e}") from e
            
            # Create temporary directory for Chrome user data
            temp_dir = tempfile.mkdtemp(prefix="playwright-debug-")
            logger.debug(f"Created temp directory: {temp_dir}")
            
            # Start Chrome with remote debugging enabled on OS-assigned port
            try:
                proc = subprocess.Popen([
                    chrome_path,
                    f"--remote-debugging-port={debug_port}",
                    f"--user-data-dir={temp_dir}"
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                logger.error(f"Failed to start Chrome process: {e}")
                raise RuntimeError(f"Chrome startup failed: {e}") from e
            
            # Wait for Chrome debug endpoint to be ready using polling
            try:
                wait_for_chrome_debug_endpoint(debug_port)
                # Chrome has successfully bound to the port, safe to close the temporary socket
                if temp_socket:
                    temp_socket.close()
                    temp_socket = None
                    logger.debug(f"Released temporary socket after Chrome bind confirmation")
            except TimeoutError as e:
                logger.error(f"Chrome debug endpoint failed to start: {e}")
                # Log process output if available for debugging
                if proc and proc.stderr:
                    try:
                        stderr_output = proc.stderr.read().decode('utf-8', errors='ignore')
                        if stderr_output:
                            logger.error(f"Chrome stderr output: {stderr_output[:500]}")
                    except Exception:
                        pass
                raise
            
            # Query the debugger endpoint to extract User-Agent
            try:
                response = requests.get(f"http://localhost:{debug_port}/json/version", timeout=5)
                response.raise_for_status()
                data = response.json()
                user_agent = data.get("User-Agent", "")
                logger.info(f"Extracted User Agent: {user_agent}")
                ua_cache = user_agent
                return user_agent
            except requests.RequestException as e:
                logger.error(f"❌ Error querying debugger endpoint: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ Error parsing response: {e}")
                raise
        except Exception as e:
            logger.error(f"❌ Error extracting UA: {e}")
            # Fallback to current Chrome UA if extraction fails
            fallback_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            ua_cache = fallback_ua
            return fallback_ua
        finally:
            # Cleanup: terminate process and remove temp directory
            if proc is not None:
                try:
                    proc.terminate()
                    # Wait for process to terminate with timeout
                    try:
                        proc.wait(timeout=10)  # 10 second timeout
                    except subprocess.TimeoutExpired:
                        logger.warning("Chrome process did not terminate within timeout, killing...")
                        proc.kill()
                        proc.wait(timeout=5)  # Give it a bit more time after kill
                except Exception as e:
                    logger.error(f"Error terminating Chrome process: {e}")
                    # Try to kill if terminate failed
                    try:
                        proc.kill()
                        proc.wait(timeout=5)
                    except Exception as kill_error:
                        logger.error(f"Error killing Chrome process: {kill_error}")
            
            # Close temporary socket if still open (cleanup in case of errors)
            if temp_socket is not None:
                try:
                    temp_socket.close()
                    logger.debug("Closed temporary socket in finally block")
                except Exception as e:
                    logger.debug(f"Error closing temporary socket: {e}")
            
            # Remove temp directory if it exists
            if temp_dir is not None:
                try:
                    if Path(temp_dir).exists():
                        shutil.rmtree(temp_dir)
                        logger.debug(f"Removed temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Error removing temp directory {temp_dir}: {e}")

# Setup browser with real UA and stealth features
# This version uses system Chrome with anti-detection measures.
# Args:
#     headless: Whether to run browser in headless mode (default: False)
# Returns:
#     tuple: (playwright, browser, context, page)
def setup_browser(headless=False):
    # Extract real UA once
    real_ua = get_chrome_user_agent()
    
    playwright = sync_playwright().start()
    
    # Initialize stealth configuration with custom overrides
    stealth_config = Stealth(
        navigator_user_agent_override=real_ua,
        navigator_vendor_override="Google Inc.",
        navigator_platform_override="Win32",
        webgl_vendor_override="Intel Inc.",
        webgl_renderer_override="Intel Iris OpenGL Engine"
    )
    
    # Use system installed Chrome, not Chromium
    browser = playwright.chromium.launch(
        channel="chrome",  # Use real Chrome instead of Chromium
        headless=headless,
        args=['--disable-blink-features=AutomationControlled']
    )
    
    context = browser.new_context(
        user_agent=real_ua,  # Real extracted UA
        locale='en-US',
        timezone_id='America/Chicago',  # Dallas timezone
        viewport={"width": 1920, "height": 1080},
        extra_http_headers={
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
    )
    
    page = context.new_page()
    
    # Apply stealth scripts to the page using the new API
    stealth_config.apply_stealth_sync(page)
    
    # Additional stealth patches
    page.add_init_script("""
        // Remove more Playwright markers
        delete window.__playwright__binding__;
        delete window.__pwInitScripts;
        
        // Patch Chrome-specific properties
        Object.defineProperty(window, 'chrome', {
            get: () => ({
                runtime: {},
                loadTimes: () => ({}),
            }),
        });
        
        // Randomize canvas fingerprints
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {
            if (this.width === 280 && this.height === 60) {
                return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
            }
            return originalToDataURL.apply(this, arguments);
        };
    """)
    
    logger.info("Browser initialized with stealth features")
    return playwright, browser, context, page

# Configuration validation functions
# Validate configuration values from config.py.
# Returns:
#     tuple: (is_valid: bool, error_message: str)
def validate_config():
    from config import ATTORNEYS, CHARGE_KEYWORDS
    
    # Validate attorneys from config
    if not ATTORNEYS or len(ATTORNEYS) == 0:
        return False, (
            "Error: ATTORNEYS list must be set in config.py with at least one attorney\n"
            "Please update config.py with the attorney information.\n"
            "Example format:\n"
            '  ATTORNEYS = [{"first_name": "JOHN", "last_name": "DOE"}]'
        )
    
    # Validate attorney structure
    for idx, attorney in enumerate(ATTORNEYS):
        if not isinstance(attorney, dict):
            return False, f"Error: Attorney {idx+1} must be a dictionary"
        if "first_name" not in attorney or "last_name" not in attorney:
            return False, f"Error: Attorney {idx+1} must have 'first_name' and 'last_name' keys"
        if not attorney["first_name"] or not attorney["last_name"]:
            return False, f"Error: Attorney {idx+1} first_name and last_name cannot be empty"
    
    # Validate charge keywords
    if not CHARGE_KEYWORDS or len(CHARGE_KEYWORDS) == 0:
        return False, (
            "Error: CHARGE_KEYWORDS list must be set in config.py with at least one keyword\n"
            "Please update config.py with charge keywords.\n"
            "Example format:\n"
            '  CHARGE_KEYWORDS = ["ASSAULT", "THEFT"]'
        )
    
    return True, None


# Display current configuration to console
def display_config():
    from config import ATTORNEYS, CHARGE_KEYWORDS
    
    print(f"\nAttorneys to search ({len(ATTORNEYS)}):")
    for idx, attorney in enumerate(ATTORNEYS, 1):
        print(f"  {idx}. {attorney['first_name']} {attorney['last_name']}")
    
    print(f"\nCharge keywords to filter ({len(CHARGE_KEYWORDS)}):")
    for idx, keyword in enumerate(CHARGE_KEYWORDS, 1):
        print(f"  {idx}. {keyword}")

