"""
Configuration file for Dallas County Scraper
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Website URL
BASE_URL = "https://courtsportal.dallascounty.org/DALLASPROD/Home/Dashboard/29"

# Browser settings
HEADLESS = False  # Set to True to run in background
# Chrome executable path (configurable via CHROME_PATH environment variable)
CHROME_PATH = os.getenv("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe")

# Wait times (in seconds)
EXPLICIT_WAIT = 20
PAGE_LOAD_TIMEOUT = 30

# Captcha settings
CAPTCHA_API_KEY = ""  # Manually set your 2Captcha or AntiCaptcha API key here
USE_CAPTCHA_SERVICE = True  # Set to True if using captcha solving service

# Search settings
ITEMS_PER_PAGE = 200  # Preferred items per page. DO NOT CHANGE THIS VALUE.
CASE_TYPE = "FELONY"  # Case type label to target when filtering the results list

# Search Criteria
# List of attorneys to search for. Each entry is a dict with 'first_name' and 'last_name'
ATTORNEYS = [
    {"first_name": "DONALD", "last_name": "TRUMP"},
    {"first_name": "HILLARY", "last_name": "CLINTON"}
    # Add more attorneys here as needed:
    # {"first_name": "JOHN", "last_name": "DOE"},
]

# List of charge keywords to search for in case descriptions
CHARGE_KEYWORDS = [
    "ASSAULT",
    # Add more keywords here as needed:
    # "THEFT",
    # "BURGLARY",
]

# Date filtering
# Minimum year for case filtering (configurable via MINIMUM_CASE_YEAR environment variable)
MINIMUM_CASE_YEAR = int(os.getenv("MINIMUM_CASE_YEAR", "2025"))  # Only process cases filed on or after this year

# Test / debug settings
ACTION_DELAY_SECONDS = 3  # Delay (in seconds) before each browser action for initial testing

# Session recovery settings
ENABLE_SESSION_RECOVERY = True  # Set to True to auto-restart session when navigation fails

# Output settings
OUTPUT_DIR = "results"
OUTPUT_FORMAT = "excel"  # Options: "csv", "json", "excel"

