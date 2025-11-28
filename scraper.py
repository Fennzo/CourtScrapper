"""
Main scraper class for Dallas County Courts Portal - Using Playwright
Each scraper instance handles one attorney.
"""
from datetime import datetime
import logging
import time

from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError
)

from captcha_handler import resolve_captcha
from case_data_extractor import check_for_charge_keyword, extract_case_details
from config import (
    ACTION_DELAY_SECONDS,
    BASE_URL,
    CAPTCHA_API_KEY,
    CASE_TYPE,
    CHARGE_KEYWORDS,
    ENABLE_SESSION_RECOVERY,
    EXPLICIT_WAIT,
    HEADLESS,
    MINIMUM_CASE_YEAR,
    PAGE_LOAD_TIMEOUT,
    USE_CAPTCHA_SERVICE,
)
from utils import setup_browser

logger = logging.getLogger(__name__)

class DallasCountyScraper:
        
    # Initialize scraper for a single attorney.
    # Args:
    # attorney: Attorney dict with 'first_name' and 'last_name'
    def __init__(self, attorney):

        if not attorney:
            raise ValueError("Attorney is required")
        
        self.attorney = attorney
        self.current_attorney_case_count = 0  # Track cases for current attorney
        self.case_type_filter = (CASE_TYPE or "").strip().lower()
        self.playwright = None
        self.browser = None
        self.page = None
        self.context = None
        self.results = []
        self.processed_case_numbers = set()  # Track processed cases for recovery
        
        # Setup browser for this scraper instance
        try:
            self.playwright, self.browser, self.context, self.page = setup_browser(headless=HEADLESS)
            # Set default timeout for this page
            self.page.set_default_timeout(EXPLICIT_WAIT * 1000)  # Convert to milliseconds
            attorney_name = f"{self.attorney['first_name']} {self.attorney['last_name']}"
            logger.info(f"Playwright browser initialized successfully for evaluating cases by {attorney_name}")
        except Exception as e:
            logger.error(f"Error setting up browser: {e}")
            raise

    # Pause briefly for each action.
    def pause_before_action(self, description: str = ""):
        try:
            delay = max(0, ACTION_DELAY_SECONDS)
        except TypeError:
            delay = 0

        if delay <= 0:
            return

        if description:
            logger.debug(f"Waiting {delay}s before {description}")
        time.sleep(delay)
    
    # Wait until the page is idle (or time out) before moving forward. Used to manually confirm page action
    def wait_for_page_load(self, timeout=30):
        try:
            # Playwright automatically waits for load state, but we can wait for network idle
            self.page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            logger.debug("Page load confirmed")
            return True
        except PlaywrightTimeoutError:
            logger.warning("Page load timeout, but continuing...")
            return False
    
    # Click a navigational element and wait for the resulting page/view to finish loading.
    def click_and_wait_for_navigation(self, element, description="", timeout=5000, post_wait=2):
        action_desc = description or "clicking element"
        try:
            self.pause_before_action(action_desc)
            element.click(timeout=timeout)
            self.wait_for_page_load()
            if post_wait:
                time.sleep(post_wait)
            return True
        except PlaywrightTimeoutError as e:
            logger.debug(f"Timeout {action_desc}: {e}")
            return False
        except Exception as e:
            logger.debug(f"Failed {action_desc}: {e}")
            return False
    
    # Open the courts dashboard, stabilize the DOM, and prep the workspace.
    def navigate_to_search_page(self):
        try:
            logger.info(f"Navigating to {BASE_URL}")
            self.pause_before_action("navigating to search page")
            self.page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT * 1000)
            
            # Wait for page to load
            self.wait_for_page_load()
            time.sleep(2)  # Additional wait for dynamic content
            
            logger.info("Successfully navigated to search page")
            return True
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout navigating to search page: {e}")
            return False
        except PlaywrightError as e:
            logger.error(f"Playwright error navigating to search page: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error navigating to search page: {e}")
            return False
    
    # Reveal the advanced filtering UI so we can tweak the search type.
    def expand_advanced_options(self):
        try:
            logger.info("Expanding Advanced Filtering Options...")
            
            # Try multiple selectors for the expand button
            expand_selectors = [
                "text=Advanced Filtering Options",
                "a:has-text('Advanced')",
                "button:has-text('Advanced')",
                "[class*='advanced']",
                "[id*='advanced']"
            ]
            
            for selector in expand_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible(timeout=5000):
                        self.pause_before_action("expanding advanced options")
                        element.click(timeout=5000)
                        time.sleep(2)
                        logger.info(f"Advanced options expanded using selector: {selector}")
                        return True
                except PlaywrightTimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Element not interactable with selector {selector}: {e}")
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error expanding advanced options: {e}")
            return False
    
    # Switch the filter dropdown in the General Options box into “Attorney Name”.
    def select_attorney_name_from_dropdown(self):
        try:
            logger.info("Selecting 'Attorney Name' from search type filter...")

            combo_input = self.page.locator("input[name='caseCriteria.SearchBy_input']").first
            if combo_input.is_visible(timeout=5000):
                self.pause_before_action("opening Search By combobox input")
                combo_input.click(timeout=5000)
                combo_input.fill("")
                combo_input.type("Attorney Name", delay=50)
                
                option_selectors = [
                    "div[role='option']:has-text('Attorney Name')",
                    "li[role='option']:has-text('Attorney Name')",
                    ".k-list li:has-text('Attorney Name')"
                ]
                
                for option_selector in option_selectors:
                    option = self.page.locator(option_selector).first
                    try:
                        if option and option.is_visible(timeout=2000):
                            self.pause_before_action("selecting 'Attorney Name' option")
                            option.click(timeout=2000)
                            logger.info("Selected 'Attorney Name' from dropdown via option click")
                            time.sleep(1)
                            return True
                    except PlaywrightTimeoutError:
                        continue
                    except Exception as e:
                        logger.debug(f"Option selector {option_selector} failed: {e}")
                        continue
                
                self.pause_before_action("confirming 'Attorney Name' entry via keyboard")
                self.page.keyboard.press("ArrowDown")
                self.page.keyboard.press("Enter")
                logger.info("Selected 'Attorney Name' from dropdown via keyboard entry fallback")
                time.sleep(1)
                return True

            logger.error("Could not locate Search By combobox input")
            return False
        except PlaywrightTimeoutError:
            logger.error("Timed out selecting attorney name filter")
            return False
        except Exception as e:
            logger.error(f"Error selecting attorney name filter: {e}")
            return False
    
    # Enter the configured attorney first/last names into Attorney Name search fields.
    def fill_search_fields(self):
        try:
            first_name = self.attorney["first_name"]
            last_name = self.attorney["last_name"]
            
            logger.info(f"Filling search fields: Last name={last_name}, First name={first_name}")

            last_input = self.page.locator("input#caseCriteria_NameLast, input[name='caseCriteria.NameLast']").first
            if not last_input.is_visible(timeout=5000):
                logger.error("Could not locate Attorney Name last-name input")
                return False
            last_input.clear()
            self.pause_before_action("filling last name")
            last_input.fill(last_name)
            logger.info("Last name filled")

            first_input = self.page.locator("input#caseCriteria_NameFirst, input[name='caseCriteria.NameFirst']").first
            if not first_input.is_visible(timeout=5000):
                logger.error("Could not locate Attorney Name first-name input")
                return False
            first_input.clear()
            self.pause_before_action("filling first name")
            first_input.fill(first_name)
            logger.info("First name filled")

            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error filling search fields: {e}")
            return False
    

    # Locate and click the submit button.
    def click_submit_button(self):
        logger.info("Looking for submit button...")
        submit_selectors = [
            "input[type='submit']",
            "button[type='submit']",
            "button:has-text('Submit')",
            "input[value*='Submit']",
            "button.btn-primary",
            "input.btn-primary"
        ]
        for selector in submit_selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible(timeout=10000) and element.is_enabled():
                    if self.click_and_wait_for_navigation(element, "clicking submit button", timeout=10000):
                        logger.info(f"Submit button clicked using selector: {selector}")
                        return True
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Submit button not interactable with selector {selector}: {e}")
                continue
        
        logger.error("Could not find or click submit button")
        return False
    
    # Check the file date of the first row in the results table.
    # Verifies the date is >= MINIMUM_CASE_YEAR from config.
    # Targets the specific file date element: <td class="card-data party-case-filedate" data-label="File Date">
    def check_latest_file_date(self):

        try:
            logger.info("Checking first row file date...")
            time.sleep(3)  # Wait for results to load
            
            # Target the specific file date element in the first row
            file_date_selectors = [
                "td.card-data.party-case-filedate[data-label='File Date']",
                "td[data-label='File Date']",
                "td.party-case-filedate",
                "td.card-data[data-label='File Date']"
            ]
            
            date_element = None
            date_text = None
            
            for selector in file_date_selectors:
                try:
                    # Get the first occurrence (first row's file date)
                    element = self.page.locator(selector).first
                    if element.count() > 0:
                        date_text = element.text_content()
                        if date_text and date_text.strip():
                            date_element = element
                            logger.info(f"Found file date element using selector: {selector}")
                            logger.info(f"File date text: {date_text.strip()}")
                            break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not date_element or not date_text:
                logger.warning("Could not locate file date element in first row")
                return True  # Proceed if we can't find the date
            
            # Parse the date
            from datetime import datetime
            date_text = date_text.strip()
            
            try:
                # Try MM/DD/YYYY format (most common)
                parsed_date = datetime.strptime(date_text, '%m/%d/%Y')
                logger.info(f"First row file date: {parsed_date.strftime('%m/%d/%Y')}")
                
                if parsed_date.year >= MINIMUM_CASE_YEAR:
                    logger.info(f"First row case is from {parsed_date.year} (>= {MINIMUM_CASE_YEAR}), proceeding...")
                    return True
                else:
                    logger.info(f"First row case is from {parsed_date.year} (< {MINIMUM_CASE_YEAR}). Skipping this attorney.")
                    return False
                    
            except ValueError:
                # Try alternative formats
                date_formats = ['%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']
                for date_format in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_text, date_format)
                        logger.info(f"First row file date: {parsed_date.strftime('%m/%d/%Y')}")
                        
                        if parsed_date.year >= MINIMUM_CASE_YEAR:
                            logger.info(f"First row case is from {parsed_date.year} (>= {MINIMUM_CASE_YEAR}), proceeding...")
                            return True
                        else:
                            logger.info(f"First row case is from {parsed_date.year} (< {MINIMUM_CASE_YEAR}). Skipping this attorney.")
                            return False
                    except ValueError:
                        continue
                
                logger.warning(f"Could not parse date '{date_text}', proceeding anyway")
                return True  # Proceed if we can't parse the date
                
        except Exception as e:
            logger.error(f"Error checking first row file date: {e}")
            return True  # Proceed on error
    
    # Attempt to increase the results page size to 200 rows.
    def set_items_per_page(self):
        try:
            logger.info("Looking for items per page selector...")
            
            pager_sizes = self.page.locator("span.k-pager-sizes").first
            if pager_sizes.count() > 0:
                hidden_select = pager_sizes.locator("select[data-role='dropdownlist']").first
                try:
                    self.pause_before_action("setting items per page via dropdown")
                    hidden_select.select_option(value="200", timeout=5000, force=True)
                    self.wait_for_page_load()
                    logger.info("Set items per page to 200 via dropdown")
                    time.sleep(2)
                    return True
                except Exception:
                    logger.debug("Dropdown selection failed; trying visible dropdown UI.")

                if pager_sizes.is_visible(timeout=3000):
                    trigger = pager_sizes.locator("span.k-input").first
                    self.pause_before_action("opening pager sizes dropdown")
                    trigger.click(timeout=5000)

                    option = self.page.locator("ul[role='listbox'] li:has-text('200')").first
                    if option.is_visible(timeout=5000):
                        if self.click_and_wait_for_navigation(option, "selecting 200 rows per page", timeout=5000):
                            logger.info("Set items per page to 200 via pager dropdown")
                            time.sleep(2)
                            return True
                    else:
                        logger.error("200 option not found in pager dropdown")
            else:
                logger.debug("Pager sizes container not found; falling back to select element.")

            pagination_selectors = [
                "select[name*='page']",
                "select[name*='items']",
                "select[id*='page']",
                "select[id*='items']"
            ]
            
            for selector in pagination_selectors:
                try:
                    select_element = self.page.locator(selector).first
                    if select_element.is_visible(timeout=5000):
                        try:
                            self.pause_before_action("setting items per page to 200")
                            select_element.select_option(label="200", timeout=5000)
                            self.wait_for_page_load()
                            logger.info("Set items per page to 200")
                            time.sleep(2)
                            return True
                        except:
                            try:
                                self.pause_before_action("setting items per page to 200 (value)")
                                select_element.select_option(value="200", timeout=5000)
                                self.wait_for_page_load()
                                logger.info("Set items per page to 200")
                                time.sleep(2)
                                return True
                            except:
                                options = select_element.locator("option").all()
                                for option in options:
                                    text = option.text_content()
                                    if text and "200" in text:
                                        select_element.select_option(value=option.get_attribute("value"), timeout=5000)
                                        self.wait_for_page_load()
                                        logger.info(f"Set items per page to {text}")
                                        time.sleep(2)
                                        return True
                            continue
                except PlaywrightTimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            logger.info("Items per page selector not found, using default")
            return False
        except Exception as e:
            logger.warning(f"Error setting items per page: {e}")
            return False
    
    # Collect every visible row whose text includes the configured case type.
    def get_case_type_rows(self):
        try:
            # Try multiple selectors for case rows
            row_selectors = [
                "table tr:not(:first-child)",  # Skip header row
                "tbody tr",
                "[class*='case-row']",
                "tr:has(a[href*='case'])"
            ]
            
            target_case_type = self.case_type_filter
            case_type_rows = []
            for selector in row_selectors:
                try:
                    elements = self.page.locator(selector).all()
                    if not elements:
                        continue

                    filtered_rows = []
                    for element in elements:
                        text = (element.text_content() or "").lower()
                        if target_case_type in text:
                            filtered_rows.append(element)

                    if filtered_rows:
                        case_type_rows = filtered_rows
                        break
                except:
                    continue
            
            if not case_type_rows:
                logger.info(f"No rows matched case type filter '{target_case_type}'")
            return case_type_rows
        except Exception as e:
            logger.error(f"Error getting case rows: {e}")
            return []
    
    # Read the textual case-type cell from the provided row.
    def extract_case_type_from_row(self, row):
        try:
            # Try to find case type in the row
            cells = row.locator("td").all()
            for cell in cells:
                text = (cell.text_content() or "").strip().lower()
                if "felony" in text:
                    return text
            return ""
        except:
            return ""
    
    # Extract the case number text from the row if available.
    def get_case_number_from_row(self, row):
        try:
            primary_link = row.locator("a.caseLink, a[data-caseid]").first
            if primary_link and primary_link.count() > 0 and primary_link.is_visible(timeout=3000):
                text = primary_link.text_content() or ""
                return text.strip()

            fallback_link = row.locator("td:first-child a, a[href*='CaseDetail']").first
            if fallback_link and fallback_link.count() > 0 and fallback_link.is_visible(timeout=3000):
                text = fallback_link.text_content() or ""
                return text.strip()
        except Exception:
            pass
        return ""
    
    # Open the case detail view by clicking the row’s hyperlink.
    def click_case_link(self, row, case_number=None):
        try:
            # Look for case number link
            link_selectors = [
                "a.caseLink[data-caseid]",
                "a[data-url*='CaseDetail']",
                "a[href*='CaseDetail']",
                "a[href*='case']",
                "a[href*='detail']",
                "td:first-child a",
                "a"
            ]
            
            for selector in link_selectors:
                try:
                    link = row.locator(selector).first
                    if not link or link.count() == 0:
                        continue
                    if link.is_visible(timeout=5000):
                        case_label = case_number or (link.text_content() or "")
                        logger.info(f"Clicking case number: {case_label.strip()}")
                        if self.click_and_wait_for_navigation(link, "opening case details", timeout=5000):
                            return True
                except PlaywrightTimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Case link not interactable with selector {selector}: {e}")
                    continue
            
            logger.warning("Could not find case link in row")
            return False
        except Exception as e:
            logger.error(f"Error clicking case link: {e}")
            return False
    
    # Inspect a case detail page and capture data when any charge keyword matches.
    def process_case_details(self):
        try:
            if not check_for_charge_keyword(self.page, CHARGE_KEYWORDS):
                return None
            
            logger.info(f"Charge keyword found, extracting case details...")
            case_data = extract_case_details(self.page)
            
            if case_data:
                # Add attorney information to the case data
                attorney_name = f"{self.attorney['first_name']} {self.attorney['last_name']}"
                case_data["attorney_name"] = attorney_name
                case_data["attorney_first_name"] = self.attorney['first_name']
                case_data["attorney_last_name"] = self.attorney['last_name']
                
                self.results.append(case_data)
                self.current_attorney_case_count += 1
                case_number = case_data.get("case_number", "UNKNOWN CASE NUMBER")
                logger.info(
                    f"Case added to results: {case_number} for attorney {case_data['attorney_name']} "
                    f"(attorney case #{self.current_attorney_case_count}, total cases: {len(self.results)})"
                )
                return case_data
            
            logger.warning("Case details extraction returned no data, skipping...")
            return None
        except Exception as e:
            logger.error(f"Error processing case details: {e}")
            return None
    
    # Return from the case detail page back to the results grid.
    def navigate_back_to_search_results(self):
        try:
            logger.info("Navigating back to search results page")
            self.pause_before_action("clicking 'Search Results' tab")
            
            search_tab_selectors = [
                "a#tcControllerLink_1",
                "li#tcController_1 a",
                "a:has-text('Search Results')",
                "p.step-label:has-text('Search Results')"
            ]
            logger.debug(f"Search results tab selectors to evaluate: {search_tab_selectors}")
            
            total_selectors = len(search_tab_selectors)
            for attempt, selector in enumerate(search_tab_selectors, start=1):
                logger.debug(
                    f"Attempt {attempt}/{total_selectors} to return to results using selector '{selector}'"
                )
                try:
                    locator = self.page.locator(selector)
                    try:
                        match_count = locator.count()
                    except Exception as count_exc:
                        logger.debug(f"Unable to count elements for selector '{selector}': {count_exc}")
                        match_count = 0

                    if match_count == 0:
                        logger.debug(f"Selector '{selector}' did not match any nodes, moving on")
                        continue

                    tab_element = locator.first
                    logger.debug(f"Selector '{selector}' located {match_count} node(s); checking visibility")

                    if tab_element.is_visible(timeout=5000):
                        logger.info(f"Clicking search results selector '{selector}'")
                        tab_element.click(timeout=5000)
                        navigated = self.wait_for_search_results_page()
                        logger.debug(
                            f"wait_for_search_results_page returned {navigated} after clicking '{selector}'"
                        )
                        if navigated:
                            logger.info("Navigated back to results page")
                            return True
                        logger.warning(
                            "Clicked a search results selector but the destination page was not confirmed"
                        )
                    else:
                        logger.debug(f"Selector '{selector}' located but not visible within timeout window")
                except PlaywrightTimeoutError:
                    logger.debug(f"Timeout while interacting with selector '{selector}'")
                    continue
                except Exception as e:
                    logger.debug(f"Selector {selector} failed when returning to results: {e}")
                    continue
            
            logger.debug("Exhausted all search results selectors without success")
            logger.error("Unable to locate 'Search Results' tab to return to the results list")
            return False
        except PlaywrightError as e:
            logger.error(f"Playwright error navigating back: {e}")
            return False
        except Exception as e:
            logger.error(f"Error navigating back to results: {e}")
            return False

    # Wait indefinitely until the party search results content in the search result page is present
    def wait_for_search_results_page(self, max_wait_seconds=120):
        try:
            logger.info("Waiting for 'Party Search Results' view to finish loading...")
            timeout_ms = max_wait_seconds * 10
            logger.debug(
                f"Waiting for 'Party Search Results' heading with timeout {timeout_ms} ms "
                f"({max_wait_seconds} logical seconds)"
            )
            # Wait for heading as a metric whether search results page has been loaded succesfully
            self.page.wait_for_selector("text=Party Search Results", timeout=timeout_ms)

            logger.info("'Party Search Results' view confirmed with data")
            return True
            
        except PlaywrightTimeoutError:
            logger.error(f"Search results did not load within {max_wait_seconds} seconds")
            return False
        except Exception as exc:
            logger.error(f"Error waiting for search results: {exc}")
            return False        
    
    # Process all felony cases currently visible on the active results page.
    def process_felony_cases(self, felony_rows):
        try:
            if not felony_rows:
                logger.info("No felony cases found on the current page")
                return
            
            # Use while loop with index so we can properly handle recovery
            i = 0
            while i < len(felony_rows):
                try:
                    # Always get fresh row reference from current felony_rows
                    row = felony_rows[i]
                    
                    logger.info(f"Processing felony case {i+1} of {len(felony_rows)} on current page...")
                    
                    case_number = self.get_case_number_from_row(row)
                    if case_number:
                        logger.info(f"Processing case number: {case_number}")
                        
                        # Skip if already processed (during recovery)
                        if case_number in self.processed_case_numbers:
                            logger.info(f"Skipping already processed case: {case_number}")
                            i += 1
                            continue
                    else:
                        logger.info("Processing case with unknown case number")

                    if self.click_case_link(row, case_number):
                        self.process_case_details()
                        
                        # Mark case as processed before navigating back
                        if case_number:
                            self.processed_case_numbers.add(case_number)
                        
                        nav_success = self.navigate_back_to_search_results()
                        
                        if not nav_success:
                            # Navigation failed - attempt session recovery if enabled
                            if ENABLE_SESSION_RECOVERY:
                                logger.warning(f"Navigation back failed after case {case_number}, attempting session recovery...")
                                recovery_success = self.recover_session()
                                if not recovery_success:
                                    logger.error("Session recovery failed, stopping processing")
                                    return
                                logger.info("Session recovered successfully, continuing from where we left off")
                                # Refresh felony rows after recovery and restart from beginning
                                # (processed cases will be skipped via processed_case_numbers)
                                felony_rows = self.get_case_type_rows()
                                i = 0
                                continue
                            else:
                                logger.error(f"Navigation back failed after case {case_number}, session recovery disabled")
                                return
                        
                        # Refresh felony rows after returning to the list
                        felony_rows = self.get_case_type_rows()
                    
                    i += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {i+1}: {e}")
                    # Attempt recovery on any exception during case processing if enabled
                    if ENABLE_SESSION_RECOVERY:
                        logger.warning("Attempting session recovery after processing error...")
                        if self.recover_session():
                            logger.info("Session recovered, continuing processing")
                            # Refresh and restart from beginning (processed cases will be skipped)
                            felony_rows = self.get_case_type_rows()
                            i = 0
                            continue
                        else:
                            logger.error("Session recovery failed")
                            return
                    else:
                        logger.error("Session recovery disabled, continuing to next case")
                        i += 1
                        continue
        except Exception as e:
            logger.error(f"Error processing felony cases on current page: {e}")

    
    # Recover the session by restarting the browser and navigating back to search results and starting evaluation from the last non processed case
    def recover_session(self, max_retries=6):
        # Close existing browser resources once before retry loop
        # (cleanup is idempotent, but no need to call it multiple times)
        self.cleanup()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Session recovery attempt {attempt + 1} of {max_retries}...")
                
                # Wait a moment before restarting
                time.sleep(2)
                
                # Reinitialize browser
                try:
                    self.playwright, self.browser, self.context, self.page = setup_browser(headless=HEADLESS)
                    self.page.set_default_timeout(EXPLICIT_WAIT * 1000)
                    logger.info("Browser reinitialized after recovery")
                except Exception as e:
                    logger.error(f"Error reinitializing browser during recovery: {e}")
                    continue
                
                # Navigate to search page
                if not self.navigate_to_search_page():
                    logger.warning(f"Recovery attempt {attempt + 1}: Failed to navigate to search page")
                    continue
                
                # Expand advanced options
                self.expand_advanced_options()
                
                # Select attorney name filter
                if not self.select_attorney_name_from_dropdown():
                    logger.warning(f"Recovery attempt {attempt + 1}: Failed to select attorney name filter")
                    continue
                
                # Fill search fields
                if not self.fill_search_fields():
                    logger.warning(f"Recovery attempt {attempt + 1}: Failed to fill search fields")
                    continue
                
                # Resolve captcha
                if not resolve_captcha(
                    self.page,
                    api_key=CAPTCHA_API_KEY if USE_CAPTCHA_SERVICE else None,
                    use_service=USE_CAPTCHA_SERVICE,
                    action_delay=ACTION_DELAY_SECONDS
                ):
                    logger.warning(f"Recovery attempt {attempt + 1}: Failed to resolve captcha")
                    continue
                
                # Submit the search form
                if not self.click_submit_button():
                    logger.warning(f"Recovery attempt {attempt + 1}: Failed to submit search")
                    continue
                
                # Wait for results
                time.sleep(3)
                
                # Expand results to 200 rows
                self.set_items_per_page()
                
                logger.info(f"Session recovery successful on attempt {attempt + 1}")
                logger.info(f"Previously processed {len(self.processed_case_numbers)} cases, will skip them")
                return True
                
            except Exception as e:
                logger.error(f"Recovery attempt {attempt + 1} failed with error: {e}")
                continue
        
        logger.error(f"Session recovery failed after {max_retries} attempts")
        return False

    # Run the scraping process for this attorney
    def run(self):

        try:
            # Step 1: Navigate to search page
            if not self.navigate_to_search_page():
                return False
            
            # Step 2: Expand advanced options
            self.expand_advanced_options()
            
            # Step 3: Select attorney name filter
            if not self.select_attorney_name_from_dropdown():
                logger.error("Could not select attorney name filter")
            
            # Step 4: Fill search fields
            if not self.fill_search_fields():
                logger.error("Could not fill search fields")
                return False
            
            # Step 5: Resolve captcha
            if not resolve_captcha(
                self.page,
                api_key=CAPTCHA_API_KEY if USE_CAPTCHA_SERVICE else None,
                use_service=USE_CAPTCHA_SERVICE,
                action_delay=ACTION_DELAY_SECONDS
            ):
                logger.error("Could not resolve captcha")
                return False

            # Step 6: Submit the search form
            if not self.click_submit_button():
                logger.error("Could not submit search")
                return False
            
            # Step 7: Check latest file date
            if not self.check_latest_file_date():
                logger.info(f"Latest case does not meet minimum year requirement ({MINIMUM_CASE_YEAR})")
                return False

            # Step 8: Expand results to 200 rows when possible
            self.set_items_per_page()

            # Step 9: Prepare felony case extraction
            logger.info("Preparing to identify felony case rows...")
            felony_rows = self.get_case_type_rows()

            # Step 10: Process felony cases 
            logger.info("Processing felony cases on current results page...")
            self.process_felony_cases(felony_rows)
            
            return True
        except Exception as e:
            logger.error(f"Error in run: {e}")
            return False
    
    # Close Playwright resources so the browser exits cleanly.
    def cleanup(self):
        try:
            if self.page:
                try:
                    self.page.close()
                except:
                    pass
                self.page = None
            if self.context:
                try:
                    self.context.close()
                except:
                    pass
                self.context = None
            if self.browser:
                try:
                    self.browser.close()
                except:
                    pass
                self.browser = None
            if self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
                self.playwright = None

            logger.info("Browser resources cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    # Return the in-memory list of scraped case dictionaries.
    def get_results(self):
        return self.results
