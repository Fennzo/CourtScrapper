"""
Captcha handling module - Using Playwright
"""
import time
import logging
import requests
import re
import threading

logger = logging.getLogger(__name__)

# Thread-local storage for use_manual_captcha_only flag: If 2captcha API fails, switch to manual for rest of the thread's session
# Each thread gets its own flag 
thread_local = threading.local()

# Get thread-local flag for manual captcha mode
def get_manual_captcha_flag():
    if not hasattr(thread_local, 'use_manual_captcha_only'):
        thread_local.use_manual_captcha_only = False
    return thread_local.use_manual_captcha_only

# Set thread-local flag for manual captcha mode
def set_manual_captcha_flag(value):
    thread_local.use_manual_captcha_only = value

# Quickly scan the page to determine whether any captcha widgets are present.
def detect_captcha(page):
    captcha_selectors = [
        "iframe[src*='recaptcha']",
        "iframe[src*='captcha']",
        ".g-recaptcha",
        "#recaptcha",
        "[data-sitekey]",
        "iframe[title*='reCAPTCHA']",
        "iframe[title*='captcha']"
    ]
    
    for selector in captcha_selectors:
        try:
            elements = page.locator(selector).all()
            if elements:
                logger.info(f"Captcha detected using selector: {selector}")
                return True, elements[0]
        except:
            continue
    
    # Also check for iframes
    try:
        iframes = page.locator("iframe").all()
        for iframe in iframes:
            src = iframe.get_attribute("src") or ""
            if "captcha" in src.lower() or "recaptcha" in src.lower():
                logger.info("Captcha iframe detected")
                return True, iframe
    except:
        pass
    
    logger.info("No captcha detected")
    return False, None

# Poll until the reCAPTCHA checkmark is visibly set (or forever if timeout=None).
def solve_captcha_manually(page, timeout=None):
    start_time = time.time()
    logger.info("Please complete the captcha in the browser window. We will constantly check for the captcha to be completed in the background.")

    while True:
        try:
            frame_locator = page.frame_locator("iframe[title='reCAPTCHA']").first
            checkbox = frame_locator.locator("span.recaptcha-checkbox").first
            if checkbox.is_visible(timeout=2000):
                aria_checked = checkbox.get_attribute("aria-checked")
                if aria_checked and aria_checked.lower() == "true":
                    logger.info("Captcha solved – checkbox marked as checked.")
                    time.sleep(1)
                    return True
        except Exception:
            pass

        if timeout is not None and (time.time() - start_time) > timeout:
            logger.warning("Captcha wait timed out.")
            return False

        time.sleep(2)

# Extract the reCAPTCHA site key value from the live DOM.
def get_recaptcha_site_key(page):
    try:
        # Method 1: Check data-sitekey attribute
        site_key_elements = page.locator("[data-sitekey]").all()
        if site_key_elements:
            site_key = site_key_elements[0].get_attribute("data-sitekey")
            if site_key:
                logger.info(f"Found reCAPTCHA site key: {site_key[:20]}...")
                return site_key
        
        # Method 2: Check in page source
        try:
            page_source = page.content()
            match = re.search(r'data-sitekey="([^"]+)"', page_source)
            if match:
                site_key = match.group(1)
                logger.info(f"Found reCAPTCHA site key from page source: {site_key[:20]}...")
                return site_key
        except:
            pass
        
        logger.warning("Could not extract reCAPTCHA site key")
        return None
    except Exception as e:
        logger.error(f"Error extracting site key: {e}")
        return None

# Submit a reCAPTCHA job to 2Captcha and inject the solved token once ready.
def solve_recaptcha_v2_with_2captcha(page, api_key, site_key=None):
    try:
        # Validate API key
        if not api_key or len(api_key) < 32:
            logger.error("Invalid 2captcha API key (must be at least 32 characters)")
            return False
        
        if not site_key:
            site_key = get_recaptcha_site_key(page)
            if not site_key:
                logger.error("Could not extract site key for 2captcha")
                return False
        
        # Validate site key format
        if not site_key or len(site_key) < 20:
            logger.error(f"Invalid reCAPTCHA site key format: {site_key}")
            return False
        
        logger.info("Submitting reCAPTCHA to 2captcha service...")
        logger.info(f"Site key: {site_key[:20]}...")
        logger.info(f"Page URL: {page.url}")
        
        # Step 1: Submit captcha to 2captcha (USING HTTPS)
        submit_url = "https://2captcha.com/in.php"
        submit_params = {
            "key": api_key,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page.url,
            "json": 1,
            "soft_id": 4582  # Software ID for tracking (register at 2captcha for your own)
        }
        
        # Retry logic for submission
        max_submit_retries = 3
        for retry in range(max_submit_retries):
            try:
                response = requests.post(submit_url, data=submit_params, timeout=30)
                response.raise_for_status()
                result = response.json()
                break
            except requests.RequestException as e:
                if retry == max_submit_retries - 1:
                    logger.error(f"Failed to submit to 2captcha after {max_submit_retries} attempts: {e}")
                    return False
                logger.warning(f"Submit attempt {retry + 1} failed, retrying...")
                time.sleep(2)
        
        # Handle submission errors
        if result.get("status") != 1:
            error_code = result.get("request", "UNKNOWN_ERROR")
            error_messages = {
                "ERROR_WRONG_USER_KEY": "Invalid API key",
                "ERROR_KEY_DOES_NOT_EXIST": "API key does not exist",
                "ERROR_ZERO_BALANCE": "No balance on 2captcha account",
                "ERROR_NO_SLOT_AVAILABLE": "No available workers (try again later)",
                "ERROR_ZERO_CAPTCHA_FILESIZE": "CAPTCHA file is too small",
                "ERROR_TOO_BIG_CAPTCHA_FILESIZE": "CAPTCHA file is too large",
                "ERROR_WRONG_FILE_EXTENSION": "Invalid file extension",
                "ERROR_IMAGE_TYPE_NOT_SUPPORTED": "Image type not supported",
                "ERROR_IP_NOT_ALLOWED": "IP not allowed (check account settings)",
                "IP_BANNED": "IP banned due to too many incorrect attempts",
                "ERROR_GOOGLEKEY": "Invalid or missing googlekey (sitekey)",
                "ERROR_PAGEURL": "Invalid or missing pageurl",
                "ERROR_BAD_TOKEN_OR_PAGEURL": "Invalid token or pageurl",
                "MAX_USER_TURN": "Queue limit reached, try again in 5 seconds"
            }
            error_msg = error_messages.get(error_code, f"Unknown error: {error_code}")
            logger.error(f"2captcha submission failed: {error_msg}")
            
            # Special handling for retry-able errors
            if error_code in ["ERROR_NO_SLOT_AVAILABLE", "MAX_USER_TURN"]:
                logger.info("Retrying in 10 seconds...")
                time.sleep(10)
                # Could recursively retry here, but keeping it simple
            
            return False
        
        captcha_id = result.get("request")
        logger.info(f"Captcha submitted successfully, request ID: {captcha_id}")
        logger.info("Waiting for solution (this typically takes 30-60 seconds)...")
        
        # Step 2: Poll for solution (USING HTTPS)
        get_url = "https://2captcha.com/res.php"
        max_attempts = 60  # 60 attempts * 5 seconds = 300 seconds max (5 minutes)
        attempt = 0
        
        # Wait at least 10 seconds before first check (workers need time)
        time.sleep(10)
        
        while attempt < max_attempts:
            get_params = {
                "key": api_key,
                "action": "get",
                "id": captcha_id,
                "json": 1
            }
            
            try:
                response = requests.get(get_url, params=get_params, timeout=30)
                response.raise_for_status()
                result = response.json()
            except requests.RequestException as e:
                logger.warning(f"Network error polling solution: {e}")
                time.sleep(5)
                attempt += 1
                continue
            
            if result.get("status") == 1:
                # Solution ready!
                token = result.get("request")
                if not token or len(token) < 100:
                    logger.error(f"Invalid token received: {token[:50] if token else 'None'}")
                    return False
                
                logger.info("Captcha solved! Token received (length: %d)", len(token))
                logger.info("Injecting token into page...")
                
                # Step 3: Inject the solution token
                return inject_recaptcha_token(page, token)
                
            elif result.get("request") in ["CAPCHA_NOT_READY", "CAPTCHA_NOT_READY"]:
                # FIXED: Handle both typo variants that 2captcha might return
                attempt += 1
                if attempt % 10 == 0:  # Log every 10 attempts (50 seconds)
                    elapsed = attempt * 5
                    logger.info(f"Still waiting for solution... ({elapsed}s elapsed, attempt {attempt}/{max_attempts})")
                time.sleep(5)
                continue
            else:
                error_code = result.get("request", "UNKNOWN_ERROR")
                error_messages = {
                    "ERROR_CAPTCHA_UNSOLVABLE": "Captcha is unsolvable (may be broken image)",
                    "ERROR_WRONG_CAPTCHA_ID": "Invalid captcha ID",
                    "ERROR_BAD_DUPLICATES": "Error: 100% recognition not achieved",
                }
                error_msg = error_messages.get(error_code, f"Unknown error: {error_code}")
                logger.error(f"2captcha polling error: {error_msg}")
                return False
        
        logger.error(f"Timeout waiting for 2captcha solution after {max_attempts * 5} seconds")
        return False
        
    except requests.RequestException as e:
        logger.error(f"Network error with 2captcha: {e}")
        logger.error("Check your internet connection and firewall settings")
        return False
    except ValueError as e:
        logger.error(f"JSON parsing error from 2captcha response: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error solving captcha with 2captcha: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Push the solved token into the hidden response field and trigger callbacks.
def inject_recaptcha_token(page, token):
    try:
        logger.info("Attempting to inject reCAPTCHA token...")
        
        # Method 1: Standard g-recaptcha-response injection
        try:
            # FIXED: Properly pass token as parameter, not using arguments
            inject_script = """
            token => {
                // Find all possible reCAPTCHA response elements
                var elements = document.querySelectorAll('textarea[name="g-recaptcha-response"]');
                if (elements.length === 0) {
                    elements = [document.getElementById('g-recaptcha-response')];
                }
                
                var injected = false;
                for (var i = 0; i < elements.length; i++) {
                    if (elements[i]) {
                        elements[i].innerHTML = token;
                        elements[i].value = token;
                        elements[i].style.display = 'block';  // Make visible for debugging
                        injected = true;
                    }
                }
                return injected;
            }
            """
            injected = page.evaluate(inject_script, token)
            if injected:
                logger.info("Token injected into g-recaptcha-response element(s)")
            else:
                logger.warning("Could not find g-recaptcha-response element")
        except Exception as e:
            logger.error(f"Standard injection method failed: {e}")
        
        # Method 2: Trigger reCAPTCHA callbacks
        try:
            # FIXED: Properly pass token as parameter
            callback_script = """
            token => {
                try {
                    // Method 2a: Call the global callback if defined
                    if (typeof ___grecaptcha_cfg !== 'undefined') {
                        var clients = ___grecaptcha_cfg.clients;
                        if (clients) {
                            for (var clientId in clients) {
                                var client = clients[clientId];
                                if (client && client.callback) {
                                    try {
                                        client.callback(token);
                                        return 'callback_executed';
                                    } catch (e) {
                                        console.log('Callback error:', e);
                                    }
                                }
                            }
                        }
                    }
                    
                    // Method 2b: Try to find and call data-callback attribute
                    var recaptchaElements = document.querySelectorAll('[data-callback]');
                    for (var i = 0; i < recaptchaElements.length; i++) {
                        var callbackName = recaptchaElements[i].getAttribute('data-callback');
                        if (callbackName && typeof window[callbackName] === 'function') {
                            try {
                                window[callbackName](token);
                                return 'data_callback_executed';
                            } catch (e) {
                                console.log('Data callback error:', e);
                            }
                        }
                    }
                    
                    // Method 2c: Dispatch custom event
                    document.dispatchEvent(new CustomEvent('recaptcha-solved', {detail: {token: token}}));
                    
                    return 'events_dispatched';
                } catch (e) {
                    return 'error: ' + e.message;
                }
            }
            """
            callback_result = page.evaluate(callback_script, token)
            logger.info(f"Callback execution result: {callback_result}")
        except Exception as e:
            logger.warning(f"Callback trigger failed: {e}")
        
        # Method 3: Mark reCAPTCHA as solved in the iframe
        try:
            mark_solved_script = """
            (function() {
                var iframes = document.querySelectorAll('iframe[src*="recaptcha"]');
                for (var i = 0; i < iframes.length; i++) {
                    try {
                        var iframeDoc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                        var checkbox = iframeDoc.querySelector('.recaptcha-checkbox-checkmark');
                        if (checkbox) {
                            checkbox.style.display = 'block';
                        }
                    } catch (e) {
                        // Cross-origin iframe, can't access
                    }
                }
            })();
            """
            page.evaluate(mark_solved_script)
        except Exception as e:
            logger.debug(f"Could not mark iframe checkbox (expected for cross-origin): {e}")
        
        logger.info("Token injection completed")
        time.sleep(3)  # Give page time to process the token
        
        # Verify token is in place
        verify_script = """
        (function() {
            var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
            if (textarea && textarea.value && textarea.value.length > 100) {
                return 'token_verified';
            }
            return 'token_not_found';
        })();
        """
        verification = page.evaluate(verify_script)
        logger.info(f"Token verification: {verification}")
        
        if verification == 'token_verified':
            logger.info("Captcha token successfully injected and verified!")
            return True
        else:
            logger.error("Token injection failed - token not found in textarea after injection")
            logger.error("This indicates the injection method did not work for this site's reCAPTCHA implementation")
            return False  # Return False to trigger fallback
        
    except Exception as e:
        logger.error(f"Critical error injecting token: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Check 2captcha account balance
# Returns balance as float, or None if error.
def check_2captcha_balance(api_key):
    try:
        url = "https://2captcha.com/res.php"
        params = {
            "key": api_key,
            "action": "getbalance",
            "json": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == 1:
            balance = float(result.get("request", 0))
            logger.info(f"2captcha account balance: ${balance:.2f}")
            return balance
        else:
            error = result.get("request", "UNKNOWN_ERROR")
            logger.warning(f"Could not retrieve balance: {error}")
            return None
            
    except Exception as e:
        logger.warning(f"Error checking 2captcha balance: {e}")
        return None

# High-level function to resolve captcha: detects, tries service, falls back to manual
# Complete captcha resolution flow: detect → try service → fallback to manual.
# Args:
#     page: Playwright page object
#     api_key: 2captcha API key (optional)
#     use_service: Whether to attempt automated solving (default: True)
#     action_delay: Delay in seconds before actions (default: 0)
# Returns:
#     bool: True if captcha resolved, False otherwise
def resolve_captcha(page, api_key=None, use_service=True, action_delay=0):
    import time
    
    logger.info("Checking for captcha...")
    
    is_captcha, _ = detect_captcha(page)
    if not is_captcha:
        logger.info("No captcha detected")
        return True
    
    logger.info("Captcha detected")
    
    # Try automated service first if enabled
    if use_service and api_key:
        logger.info("Attempting to solve captcha using 2captcha service...")
        if solve_captcha_with_service(page, api_key):
            logger.info("Captcha solved successfully via 2captcha")
            return True
        logger.warning("2captcha solving failed; manual completion required.")
    
    # Fallback to manual solving
    try:
        # Safely obtain the iframe locator - check if iframe exists first
        iframe_locator = page.locator("iframe[title='reCAPTCHA']")
        if iframe_locator.count() == 0:
            logger.error("Captcha iframe not found")
            return False
        
        # Now get the frame locator for interaction
        frame_locator = page.frame_locator("iframe[title='reCAPTCHA']")
        captcha_frame = frame_locator.first
        
        checkbox_border = captcha_frame.locator("div.recaptcha-checkbox-border").first
        if not checkbox_border.is_visible(timeout=5000):
            logger.error("Captcha checkbox border not visible inside iframe")
            return False
        
        # Add delay if specified
        if action_delay > 0:
            logger.debug(f"Waiting {action_delay}s before clicking captcha checkbox")
            time.sleep(action_delay)
        
        checkbox_border.click(timeout=5000)
        logger.info("Captcha checkbox clicked; waiting for completion...")
        
        # Add delay before manual solving
        if action_delay > 0:
            logger.debug(f"Waiting {action_delay}s before allowing user to complete captcha challenge")
            time.sleep(action_delay)
        
        if not solve_captcha_manually(page):
            logger.error("Captcha not completed after manual prompt")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error during manual captcha fallback: {e}", exc_info=True)
        return False

# Wrapper that selects the captcha solving provider and kicks off the solve.
def solve_captcha_with_service(page, api_key, service="2captcha"):
    try:
        # Check if we've already switched to manual mode (thread-local)
        if get_manual_captcha_flag():
            logger.warning("2captcha previously failed - using manual captcha resolution for this session")
            logger.info("Please solve the captcha manually in the browser window...")
            return solve_captcha_manually(page, timeout=300)  # 5 minute timeout
        
        if not api_key:
            logger.warning("No API key provided for captcha service")
            logger.info("Falling back to manual captcha resolution...")
            return solve_captcha_manually(page, timeout=300)
        
        if service.lower() == "2captcha":
            logger.info("Attempting to solve captcha with 2captcha service...")
            
            # Check balance before attempting (optional but recommended)
            balance = check_2captcha_balance(api_key)
            if balance is not None and balance < 0.003:  # Minimum ~$0.003 per reCAPTCHA
                logger.error(f"Insufficient 2captcha balance: ${balance:.4f} (need at least $0.003)")
                logger.error("Please top up your account at https://2captcha.com")
                logger.warning("Switching to manual captcha resolution for the rest of this session")
                set_manual_captcha_flag(True)
                return solve_captcha_manually(page, timeout=300)
            
            # Try to solve with 2captcha
            success = solve_recaptcha_v2_with_2captcha(page, api_key)
            
            if not success:
                # 2captcha failed - switch to manual for rest of session
                logger.error("2captcha service failed to solve captcha")
                logger.warning("Switching to manual captcha resolution for the rest of this session")
                set_manual_captcha_flag(True)
                logger.info("\n" + "="*60)
                logger.info("MANUAL CAPTCHA REQUIRED")
                logger.info("Please solve the captcha in the browser window")
                logger.info("="*60 + "\n")
                return solve_captcha_manually(page, timeout=300)
            
            return True
        else:
            logger.warning(f"Captcha service '{service}' not implemented")
            logger.info("Falling back to manual captcha resolution...")
            return solve_captcha_manually(page, timeout=300)
            
    except Exception as e:
        logger.error(f"Error in solve_captcha_with_service: {e}")
        logger.warning("Switching to manual captcha resolution for the rest of this session")
        set_manual_captcha_flag(True)
        return solve_captcha_manually(page, timeout=300)
