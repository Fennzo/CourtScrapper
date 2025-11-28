# Dallas County Courts Portal Scraper - Technical Documentation

**Version:** 2.0  
**Last Updated:** 2025-01-27  
**Status:** Production

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Module Reference](#3-module-reference)
4. [Data Flow & Processing Pipeline](#4-data-flow--processing-pipeline)
5. [Configuration & Environment](#5-configuration--environment)
6. [Design Patterns & Architectural Decisions](#6-design-patterns--architectural-decisions)
7. [API & Interface Specifications](#7-api--interface-specifications)
8. [Error Handling & Resilience](#8-error-handling--resilience)
9. [Setup & Deployment](#9-setup--deployment)
10. [Testing & Debugging](#10-testing--debugging)
11. [Performance & Scalability](#11-performance--scalability)
12. [Known Limitations & Future Enhancements](#12-known-limitations--future-enhancements)

---

## 1. Executive Summary

### 1.1 Purpose

The Dallas County Courts Portal Scraper is an automated web scraping system designed to extract case information from the Dallas County Courts Portal. It searches for cases associated with one or more attorneys, filters results by case type (default: felony) and charge keywords, and exports structured case data to CSV, Excel, or JSON formats.

### 1.2 Key Capabilities

- **Multi-Attorney Support**: Concurrently processes multiple attorneys using thread pool execution
- **Intelligent Filtering**: Filters cases by case type, charge keywords, and minimum file date
- **Captcha Handling**: Automated captcha solving via 2Captcha API with manual fallback
- **Stealth Automation**: Browser automation with anti-detection measures to mimic human behavior
- **Flexible Export**: Supports CSV, Excel (with multi-sheet formatting), and JSON output formats
- **Robust Error Handling**: Comprehensive error recovery and partial result preservation
- **Detailed Logging**: Thread-aware logging with full execution traces

### 1.3 Technology Stack

| Component | Technology |
|-----------|-----------|
| **Browser Automation** | Playwright (Chromium/Chrome) |
| **Stealth Features** | playwright-stealth |
| **Data Processing** | pandas |
| **Excel Export** | openpyxl |
| **Concurrency** | ThreadPoolExecutor (Python) |
| **Configuration** | python-dotenv |
| **Language** | Python 3.8+ |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Entry Point                                         │  │
│  │  - Configuration Validation                          │  │
│  │  - Logging Setup                                     │  │
│  │  - Result Aggregation                                │  │
│  │  - Export Orchestration                              │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   scraper_pool.py                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ThreadPoolExecutor Manager                          │  │
│  │  - Worker Thread Management                          │  │
│  │  - Result Aggregation (Thread-Safe)                  │  │
│  │  - Concurrent Attorney Processing                    │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Scraper    │ │   Scraper    │ │   Scraper    │
│  Instance 1  │ │  Instance 2  │ │  Instance N  │
│  (Attorney 1)│ │ (Attorney 2) │ │(Attorney N)  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Playwright │ │   Playwright │ │   Playwright │
│   Browser 1  │ │   Browser 2  │ │   Browser N  │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 2.2 Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      scraper.py                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  DallasCountyScraper Class                            │ │
│  │                                                        │ │
│  │  ┌──────────────────┐  ┌───────────────────────────┐ │ │
│  │  │ Navigation Layer │  │  Data Extraction Layer    │ │ │
│  │  │ - Page nav       │  │  - Case detail extract    │ │ │
│  │  │ - Form fill      │  │  - Field parsing          │ │ │
│  │  │ - Selector mgmt  │  │  - Validation             │ │ │
│  │  └────────┬─────────┘  └──────────┬────────────────┘ │ │
│  │           │                       │                   │ │
│  │  ┌────────┴───────────────────────┴──────────────┐  │ │
│  │  │           Integration Layer                    │  │ │
│  │  │  - captcha_handler.py                         │  │ │
│  │  │  - case_data_extractor.py                     │  │ │
│  │  │  - utils.py (browser setup)                   │  │ │
│  │  └───────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow Architecture

```
Configuration (config.py)
    │
    ├──► Main Entry (main.py)
    │       │
    │       ├──► Validation (utils.validate_config)
    │       │
    │       └──► Scraper Pool (scraper_pool.py)
    │               │
    │               └──► Scraper Instances (scraper.py)
    │                       │
    │                       ├──► Browser Setup (utils.setup_browser)
    │                       │       └──► Chrome User Agent Extraction
    │                       │
    │                       ├──► Navigation
    │                       │       ├──► Search Page
    │                       │       ├──► Form Filling
    │                       │       └──► Captcha Resolution
    │                       │
    │                       ├──► Results Processing
    │                       │       ├──► Date Filtering
    │                       │       ├──► Case Type Filtering
    │                       │       └──► Row Selection
    │                       │
    │                       └──► Case Extraction Loop
    │                               ├──► Case Detail Page
    │                               ├──► Keyword Filtering
    │                               ├──► Data Extraction
    │                               └──► Result Aggregation
    │
    └──► Export (result_exporter.py)
            ├──► DataFrame Conversion
            ├──► Format Conversion
            └──► File Output (CSV/Excel/JSON)
```

---

## 3. Module Reference

### 3.1 `main.py` - Application Entry Point

**Purpose**: Orchestrates the entire scraping workflow from initialization to result export.

**Key Responsibilities**:
- Configuration validation
- Logging initialization
- Scraper pool coordination
- Result aggregation and export
- Exception handling and cleanup

**Entry Point**:
```python
def main():
    logger = setup_logging()
    # ... validation and execution ...
```

**Dependencies**:
- `utils.setup_logging()`
- `utils.validate_config()`
- `utils.display_config()`
- `scraper_pool.run_all_attorneys_concurrent()`
- `result_exporter.export_results()`

**Error Handling**:
- Catches `KeyboardInterrupt` for graceful shutdown
- Exports partial results on interruption
- Comprehensive exception logging

### 3.2 `scraper.py` - Core Scraping Engine

**Purpose**: Implements the `DallasCountyScraper` class that handles browser automation and case extraction for a single attorney.

**Class: `DallasCountyScraper`**

#### 3.2.1 Initialization

```python
def __init__(self, attorney):
    """
    Args:
        attorney: dict with 'first_name' and 'last_name' keys
    """
```

**State Management**:
- `self.attorney`: Target attorney information
- `self.playwright`, `self.browser`, `self.context`, `self.page`: Browser instances
- `self.results`: Accumulated case data
- `self.processed_case_numbers`: Set of processed cases (prevents duplicates)

#### 3.2.2 Key Methods

**Navigation Methods**:
- `navigate_to_search_page()`: Opens the portal and waits for page load
- `expand_advanced_options()`: Reveals advanced search filters
- `select_attorney_name_from_dropdown()`: Configures search type filter
- `fill_search_fields()`: Populates attorney name fields

**Captcha & Submission**:
- `handle_captcha_and_submit()`: Orchestrates captcha resolution and form submission
- Uses `captcha_handler.resolve_captcha()` for automated/manual solving

**Results Processing**:
- `check_latest_file_date()`: Validates that newest case meets minimum year requirement
- `set_items_per_page()`: Attempts to increase page size for efficiency
- `get_case_type_rows()`: Filters visible rows by case type

**Case Extraction Loop**:
- `process_felony_cases()`: Main extraction loop
- `click_case_link()`: Navigates to case detail page
- `process_case_details()`: Extracts and validates case data
- `navigate_back_to_search_results()`: Returns to results list

**Utility Methods**:
- `pause_before_action()`: Implements action delays for human-like behavior
- `wait_for_page_load()`: Waits for network idle state
- `click_and_wait_for_navigation()`: Centralized click-and-wait pattern

#### 3.2.3 Design Patterns

**Error Containment**: Each case extraction is wrapped in try/except to prevent one failure from stopping the entire process.

**Selector Fallback**: Critical UI interactions use multiple selector strategies to handle DOM variations.

**State Recovery**: Uses `processed_case_numbers` set to track progress and enable recovery.

### 3.3 `scraper_pool.py` - Concurrency Manager

**Purpose**: Manages concurrent execution of multiple scraper instances using ThreadPoolExecutor.

**Key Functions**:

#### `scrape_attorney_worker(attorney, attorney_index)`
- Worker function executed by thread pool
- Creates isolated scraper instance per attorney
- Handles cleanup and error reporting
- Returns tuple: `(attorney_index, results, success, error)`

#### `run_all_attorneys_concurrent(attorneys)`
- Orchestrates thread pool execution
- Thread-safe result aggregation using `threading.Lock()`
- Tracks exceptions per worker
- Returns aggregated results list

**Concurrency Strategy**:
- **I/O-Bound Optimization**: Defaults to `max(32, CPU_COUNT * 4)` workers
- **Isolation**: Each attorney gets independent browser instance
- **Resource Management**: Automatic cleanup via `finally` blocks

**Thread Safety**:
- Result collection uses locks to prevent race conditions
- Each worker maintains independent browser context
- Logging includes thread identification for debugging

### 3.4 `case_data_extractor.py` - Data Extraction Library

**Purpose**: Provides reusable functions for extracting structured data from case detail pages.

**Key Functions**:

#### Section Extraction
- `get_section_text(page, heading_text)`: Locates section by heading and extracts text content
- `normalize_section_lines(section_text)`: Splits and cleans section text into structured lines
- `extract_value_from_lines(lines, label)`: Finds value associated with a label

#### Field Extraction
- `extract_value_by_selectors(page, selectors, regex=None)`: Multi-selector field extraction with regex support
- `ensure_field_extracted(field_label, value, required=True)`: Validates required fields
- `record_field_extraction(field_label, value, field_errors, required=True)`: Captures extraction errors

#### Specialized Extractors
- `extract_case_details(page)`: Main orchestration function for case data extraction
- `extract_charge_description(page)`: Extracts charge descriptions
- `extract_bond_amount(page)`: Extracts bond information with disqualifier filtering
- `extract_disposition(page)`: Extracts disposition and sentencing information

**Data Validation**:
- Required fields raise `FieldExtractionError` if missing
- Optional fields return empty strings
- Error tracking via `field_errors` list

**Bond Amount Filtering**:
- Uses `BOND_AMOUNT_DISQUALIFIERS` tuple to exclude non-bond amounts
- Filters out terms like "due", "owed", "fee", "fine", etc.

### 3.5 `captcha_handler.py` - Captcha Resolution

**Purpose**: Handles reCAPTCHA detection and resolution via automated service or manual completion.

**Key Functions**:

#### Detection
- `detect_captcha(page)`: Scans page for captcha widgets using multiple selectors
- Returns `(bool, element)` tuple indicating presence and location

#### Manual Solving
- `solve_captcha_manually(page, timeout=None)`: Polls for captcha completion
- Checks `aria-checked` attribute on checkbox
- Infinite or timeout-based waiting

#### Automated Solving (2Captcha)
- `solve_recaptcha_v2_with_2captcha(page, api_key, site_key=None)`: Submits captcha to 2Captcha API
- `get_recaptcha_site_key(page)`: Extracts site key from DOM
- `inject_recaptcha_token(page, token)`: Injects solved token and triggers callbacks

**Thread Safety**:
- Uses `threading.local()` for thread-specific captcha mode flags
- Prevents API failures from affecting other threads

**Error Handling**:
- Automatic fallback to manual mode on API failure
- Retry logic for network requests
- Comprehensive logging of captcha resolution stages

### 3.6 `result_exporter.py` - Export Module

**Purpose**: Converts scraped results into structured file formats with formatting.

**Key Functions**:

#### Main Export
- `export_results(results, output_dir)`: Orchestrates export process
- Creates pandas DataFrame from results
- Applies column renaming and ordering
- Routes to format-specific exporters

#### Format Exporters
- `export_csv(df, output_dir, timestamp)`: CSV export
- `export_json(df, output_dir, timestamp)`: JSON export with indentation
- `export_excel(df, output_dir, timestamp)`: Excel export with multi-sheet support

**Excel Features**:
- **Multi-Sheet Support**: Creates "All Cases" sheet plus one sheet per attorney
- **Sheet Name Sanitization**: Handles Excel's 31-character limit and invalid characters
- **Auto-Formatting**: Column width adjustment, header styling, color coding
- **Duplicate Prevention**: Unique sheet names via numbering

**Column Mapping**:
- Maps internal field names to user-friendly column titles
- Maintains logical column ordering (Attorney info first)
- Handles missing columns gracefully

### 3.7 `utils.py` - Utility Functions

**Purpose**: Provides cross-cutting utilities for browser setup, logging, and configuration.

**Key Functions**:

#### Logging
- `setup_logging()`: Configures file and console logging with thread identification
- Creates timestamped log files in `logs/` directory
- Format: `%(asctime)s - [%(threadName)s] - %(name)s - %(levelname)s - %(message)s`

#### Browser Setup
- `setup_browser(headless=False)`: Creates Playwright browser instance with stealth features
- `get_chrome_user_agent()`: Extracts real Chrome user agent from system Chrome
- `wait_for_chrome_debug_endpoint(debug_port, timeout, poll_interval)`: Polls Chrome debug endpoint

**Stealth Features**:
- Real user agent extraction from system Chrome
- Navigator property overrides
- Canvas fingerprint randomization
- Automation marker removal
- Custom HTTP headers

#### Configuration
- `validate_config()`: Validates required configuration values
- `display_config()`: Prints current configuration to console
- `create_output_dir()`: Ensures results directory exists

**Chrome User Agent Extraction**:
- Launches temporary Chrome instance with debugging
- Queries debug endpoint for real user agent
- Caches result per process for performance
- Thread-safe with locking mechanism

### 3.8 `config.py` - Configuration Management

**Purpose**: Centralizes all configuration values with environment variable support.

**Configuration Categories**:

1. **Website Settings**
   - `BASE_URL`: Target portal URL

2. **Browser Settings**
   - `HEADLESS`: Headless mode flag
   - `CHROME_PATH`: Chrome executable path (env: `CHROME_PATH`)

3. **Timing Settings**
   - `EXPLICIT_WAIT`: Explicit wait time (seconds)
   - `PAGE_LOAD_TIMEOUT`: Page load timeout (seconds)
   - `ACTION_DELAY_SECONDS`: Delay before actions (seconds)

4. **Captcha Settings**
   - `CAPTCHA_API_KEY`: 2Captcha API key
   - `USE_CAPTCHA_SERVICE`: Enable automated captcha solving

5. **Search Criteria**
   - `ATTORNEYS`: List of attorney dictionaries
   - `CHARGE_KEYWORDS`: List of charge keywords
   - `CASE_TYPE`: Case type filter (default: "FELONY")
   - `ITEMS_PER_PAGE`: Preferred page size

6. **Filtering Settings**
   - `MINIMUM_CASE_YEAR`: Minimum case file year (env: `MINIMUM_CASE_YEAR`)

7. **Output Settings**
   - `OUTPUT_DIR`: Output directory path
   - `OUTPUT_FORMAT`: Export format (csv/json/excel)

8. **Session Settings**
   - `ENABLE_SESSION_RECOVERY`: Enable session recovery on navigation failure

**Environment Variable Support**:
All settings can be overridden via environment variables or `.env` file using `python-dotenv`.

---

## 4. Data Flow & Processing Pipeline

### 4.1 End-to-End Flow

```
1. INITIALIZATION
   ├── Load configuration (config.py)
   ├── Validate settings (utils.validate_config)
   ├── Initialize logging (utils.setup_logging)
   └── Display configuration summary

2. SCRAPER POOL SETUP
   ├── Determine worker count (min(attorneys, MAX_WORKERS))
   ├── Create ThreadPoolExecutor
   └── Submit attorney tasks

3. PER-ATTORNEY EXECUTION (Concurrent)
   ├── Create scraper instance
   ├── Initialize browser (utils.setup_browser)
   │   ├── Extract Chrome user agent
   │   ├── Launch Playwright browser
   │   └── Apply stealth features
   │
   ├── NAVIGATION PHASE
   │   ├── Navigate to search page
   │   ├── Handle initial popups (optional)
   │   ├── Expand advanced options
   │   ├── Select "Attorney Name" filter
   │   └── Fill search fields
   │
   ├── CAPTCHA RESOLUTION
   │   ├── Detect captcha presence
   │   ├── If USE_CAPTCHA_SERVICE:
   │   │   ├── Extract site key
   │   │   ├── Submit to 2Captcha API
   │   │   ├── Poll for solution
   │   │   └── Inject token
   │   └── Else: Manual completion loop
   │
   ├── FORM SUBMISSION
   │   ├── Click submit button
   │   └── Wait for results page
   │
   ├── RESULTS VALIDATION
   │   ├── Check latest file date (MINIMUM_CASE_YEAR)
   │   ├── If validation fails: Exit early
   │   └── Set items per page (200)
   │
   ├── CASE FILTERING
   │   ├── Get all visible rows
   │   ├── Filter by CASE_TYPE (case-insensitive)
   │   └── Refresh selectors for DOM stability
   │
   ├── CASE EXTRACTION LOOP
   │   For each filtered row:
   │   ├── Click case link
   │   ├── Wait for case detail page
   │   ├── Check for charge keyword (case_data_extractor)
   │   │   ├── If keyword missing: Skip to next case
   │   │   └── If keyword present: Continue extraction
   │   ├── Extract case details (case_data_extractor)
   │   │   ├── Extract required fields
   │   │   ├── Extract optional fields
   │   │   └── Validate data integrity
   │   ├── Append to results
   │   └── Navigate back to results
   │
   └── CLEANUP
       ├── Close browser
       └── Stop Playwright

4. RESULT AGGREGATION
   ├── Collect results from all workers (thread-safe)
   ├── Track exceptions per worker
   └── Generate summary statistics

5. EXPORT PHASE
   ├── Convert results to DataFrame
   ├── Apply column mapping
   ├── Select export format
   ├── Generate timestamped filename
   └── Write to output directory

6. COMPLETION
   ├── Print summary statistics
   └── Exit
```

### 4.2 Data Structures

#### Attorney Dictionary
```python
{
    "first_name": str,  # Required
    "last_name": str    # Required
}
```

#### Case Result Dictionary
```python
{
    "attorney_name": str,              # Full name
    "attorney_first_name": str,        # First name
    "attorney_last_name": str,         # Last name
    "case_number": str,                # Required
    "file_date": str,                  # Required (MM/DD/YYYY)
    "judicial_officer": str,           # Required
    "case_status": str,                # Required
    "case_type": str,                  # Case type (e.g., "FELONY")
    "charge_description": str,         # Optional
    "bond_amount": str,                # Optional
    "disposition": str,                # Optional
    "sentencing_info": str             # Optional
}
```

### 4.3 Filtering Logic

**Date Filtering**:
- Parses dates in MM/DD/YYYY format (with fallback formats)
- Exits early if newest case is before `MINIMUM_CASE_YEAR`

**Case Type Filtering**:
- Filters table rows by case-insensitive substring match
- Default filter: "FELONY" (configurable via `CASE_TYPE`)
- Applied after date validation

**Charge Keyword Filtering**:
- Performed on case detail page (not results list)
- Checks if any `CHARGE_KEYWORDS` appear in page content
- Case-insensitive matching
- If no keywords found, skips case extraction entirely

---

## 5. Configuration & Environment

### 5.1 Configuration File Structure

See `config.py` for complete configuration options. All values support environment variable overrides via `.env` file.

### 5.2 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHROME_PATH` | Path to Chrome executable | Windows default |
| `MINIMUM_CASE_YEAR` | Minimum case file year | `2025` |
| `MAX_WORKERS` | Thread pool worker count | `max(32, CPU_COUNT * 4)` |
| `CAPTCHA_API_KEY` | 2Captcha API key | None |

### 5.3 Configuration Validation

The system validates configuration on startup:
- **Required**: `ATTORNEYS` list must contain at least one attorney
- **Required**: Each attorney must have `first_name` and `last_name`
- **Required**: `CHARGE_KEYWORDS` list must contain at least one keyword
- **Validation Function**: `utils.validate_config()`

### 5.4 Security Considerations

- **API Keys**: Store `CAPTCHA_API_KEY` in `.env` file (not committed to git)
- **Sensitive Data**: Logs may contain case information; sanitize before sharing
- **Browser Paths**: `CHROME_PATH` can be configured for different environments

---

## 6. Design Patterns & Architectural Decisions

### 6.1 Concurrency Pattern: Thread Pool with Isolation

**Decision**: Use `ThreadPoolExecutor` with one browser instance per attorney

**Rationale**:
- Web scraping is I/O-bound, benefiting from high concurrency
- Each attorney requires independent browser context
- Thread pool provides resource management and error isolation

**Trade-offs**:
- **Pros**: High throughput, isolated failures, resource control
- **Cons**: Higher memory usage, browser instance overhead

### 6.2 Stealth Pattern: Real User Agent + Property Masking

**Decision**: Extract real Chrome user agent and mask automation properties

**Rationale**:
- Real user agents reduce detection likelihood
- Property masking prevents bot detection scripts
- Canvas fingerprint randomization adds another layer

**Implementation**:
- System Chrome user agent extraction via debug endpoint
- `playwright-stealth` library for property masking
- Custom init scripts for additional masking

### 6.3 Error Containment Pattern: Per-Case Try/Except

**Decision**: Wrap each case extraction in individual try/except blocks

**Rationale**:
- One failed case should not stop entire scraping process
- Enables partial result collection
- Better error reporting and debugging

**Implementation**:
```python
for case_row in case_rows:
    try:
        # Extract case data
    except Exception as e:
        logger.error(f"Failed to process case: {e}")
        continue  # Skip to next case
```

### 6.4 Selector Fallback Pattern: Multiple Selector Strategies

**Decision**: Use multiple selector attempts for critical UI elements

**Rationale**:
- DOM structure may vary or change
- Reduces fragility from minor UI updates
- Provides graceful degradation

**Implementation**:
```python
selectors = [
    "primary-selector",
    "fallback-selector-1",
    "fallback-selector-2"
]
for selector in selectors:
    try:
        element = page.locator(selector)
        if element.is_visible():
            return element
    except:
        continue
```

### 6.5 State Management Pattern: Result Accumulation

**Decision**: Accumulate results in-memory, export after completion

**Rationale**:
- Simpler error handling (all-or-nothing export)
- Better performance (single DataFrame creation)
- Enables post-processing before export
---

## 7. API & Interface Specifications

### 7.1 Public Functions

#### `main.main()`
Entry point for application execution.

**Parameters**: None  
**Returns**: None  
**Side Effects**: Creates log files, exports results

#### `scraper_pool.run_all_attorneys_concurrent(attorneys)`
Executes concurrent scraping for multiple attorneys.

**Parameters**:
- `attorneys` (list[dict]): List of attorney dictionaries

**Returns**:
- `list[dict]`: Aggregated case results

**Exceptions**:
- Logs exceptions per worker, returns partial results on failure

#### `result_exporter.export_results(results, output_dir)`
Exports scraped results to configured format.

**Parameters**:
- `results` (list[dict]): List of case dictionaries
- `output_dir` (str|Path|None): Output directory (defaults to "results")

**Returns**: None  
**Side Effects**: Creates output files

#### `utils.setup_logging()`
Configures application logging.

**Returns**: `logging.Logger`  
**Side Effects**: Creates log directory and files

#### `utils.validate_config()`
Validates configuration values.

**Returns**: `tuple[bool, str|None]` - (is_valid, error_message)

---

## 8. Error Handling & Resilience

### 8.1 Error Categories

1. **Configuration Errors**: Invalid or missing configuration
   - **Handling**: Validation on startup, early exit with error message

2. **Navigation Errors**: Page load failures, timeouts
   - **Handling**: Retry logic, graceful degradation, logging

3. **Captcha Errors**: API failures, manual timeout
   - **Handling**: Fallback to manual mode, thread-local flags

4. **Extraction Errors**: Missing fields, parsing failures
   - **Handling**: Per-case try/except, skip on failure, error logging

5. **Browser Errors**: Chrome startup failures, crashes
   - **Handling**: Error propagation, cleanup in finally blocks

### 8.2 Resilience Mechanisms

**Session Recovery**:
- `ENABLE_SESSION_RECOVERY` flag enables automatic session restart on navigation failure
- Tracks processed cases to avoid duplicates on restart

**Partial Result Preservation**:
- Results accumulated incrementally
- On interruption, partial results are exported
- Keyboard interrupt handling in `main.py`

**Timeout Handling**:
- Multiple timeout levels (page load, element visibility, network idle)
- Timeouts configured via config (EXPLICIT_WAIT, PAGE_LOAD_TIMEOUT)
- Graceful degradation on timeout (log warning, continue)

**Selector Resilience**:
- Multiple selector strategies per element
- Fallback selectors for critical UI components
- Defensive element existence checks

### 8.3 Logging Strategy

**Log Levels**:
- **INFO**: Normal operation, progress updates
- **WARNING**: Non-fatal issues, fallback behavior
- **ERROR**: Failures, exceptions
- **DEBUG**: Detailed execution traces

**Thread Identification**:
- Logs include thread name for concurrent execution debugging
- Format: `[%(threadName)s]`

**File Organization**:
- One log file per execution (timestamped)
- Location: `logs/scraper_YYYYMMDD_HHMMSS.log`

---

## 9. Setup & Deployment

### 9.1 Prerequisites

- **Python**: 3.8 or higher
- **Chrome/Chromium**: Installed and accessible
- **Dependencies**: See `requirements.txt`

### 9.2 Installation Steps

1. **Clone/Download Repository**
   ```bash
   cd DallasCountyScraper
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright Browsers**
   ```bash
   playwright install chromium
   ```

4. **Configure Environment**
   - Edit `config.py` with attorney names and keywords
   - (Optional) Create `.env` file for API keys:
     ```
     CAPTCHA_API_KEY=your_api_key_here
     CHROME_PATH=C:\Path\To\Chrome.exe
     MINIMUM_CASE_YEAR=2025
     ```

5. **Run Scraper**
   ```bash
   python main.py
   ```

### 9.3 Deployment Considerations

**Production Deployment**:
- Set `HEADLESS = True` in config for server environments
- Configure `CHROME_PATH` for target system
- Use environment variables for sensitive config
- Set up log rotation for long-running processes

**Docker Deployment** (Future):
- Include Chrome in container image
- Mount volumes for logs and results
- Configure environment variables via Docker secrets

**Resource Requirements**:
- **Memory**: ~200-500MB per concurrent browser instance
- **CPU**: I/O-bound, benefits from multiple cores
- **Disk**: Logs and results accumulate over time

---

## 10. Testing & Debugging

### 10.1 Debugging Tools

**Browser Inspection**:
- Use `inspect_website.py` for selector discovery
- Run with `HEADLESS = False` for visual debugging
- Enable `ACTION_DELAY_SECONDS` to observe behavior

**Logging**:
- Review `logs/*.log` for execution traces
- Thread names help identify concurrent issues
- Search for "ERROR" or "WARNING" for problem areas

**Configuration Validation**:
- Run with invalid config to test validation
- Use `utils.display_config()` to verify settings

### 10.2 Common Issues & Solutions

**Issue**: Captcha not solving automatically
- **Solution**: Check `CAPTCHA_API_KEY` in `.env`, verify 2Captcha balance
- **Workaround**: Set `USE_CAPTCHA_SERVICE = False` for manual solving

**Issue**: "Latest case is not from 2025" error
- **Solution**: Adjust `MINIMUM_CASE_YEAR` in config or verify attorney has recent cases

**Issue**: Chrome not found
- **Solution**: Set `CHROME_PATH` environment variable to Chrome executable path

**Issue**: Timeout errors
- **Solution**: Increase `EXPLICIT_WAIT` or `PAGE_LOAD_TIMEOUT` in config

**Issue**: No cases found
- **Check**: Verify attorney names match portal exactly (case-sensitive)
- **Check**: Verify `CHARGE_KEYWORDS` match case descriptions
- **Check**: Verify `CASE_TYPE` filter (default "FELONY")

### 10.3 Testing Strategy

**Manual Testing**:
- Test with single attorney first
- Verify case extraction accuracy
- Test captcha resolution flow

**Integration Testing**:
- Test concurrent execution with multiple attorneys
- Verify thread safety of result aggregation
- Test error handling and recovery

**Edge Cases**:
- Empty results
- Network failures
- Captcha API failures
- Invalid configuration

---

## 11. Performance & Scalability

### 11.1 Performance Characteristics

**Single Attorney**:
- Navigation: ~5-10 seconds
- Captcha resolution: ~30-60 seconds (manual) or ~20-40 seconds (API)
- Case extraction: ~2-5 seconds per case
- Total: Depends on number of cases

**Concurrent Execution**:
- Throughput scales with worker count (up to resource limits)
- Default: `max(32, CPU_COUNT * 4)` workers
- Memory usage: ~200-500MB per worker

**Bottlenecks**:
- **Captcha Resolution**: Primary bottleneck (manual or API latency)
- **Network Latency**: Page loads and navigation
- **Case Detail Extraction**: Sequential per-case processing

### 11.2 Scalability Considerations

**Horizontal Scaling**:
- System can run multiple instances with different attorney sets
- Results can be aggregated post-execution
- No shared state between instances

**Vertical Scaling**:
- Increase `MAX_WORKERS` for more concurrent processing
- Limited by available memory (browser instances)
- Diminishing returns beyond 50-100 workers

**Optimization Opportunities**:
- Parallel case extraction (if portal allows)
- Caching of case detail pages (if unchanged)
- Incremental export (streaming)

### 11.3 Resource Management

**Memory**:
- Each browser instance: ~200-500MB
- Results accumulation: ~1-10MB per 1000 cases
- Logs: ~1-5MB per execution

**CPU**:
- I/O-bound workload
- Browser rendering uses CPU but is asynchronous
- Minimal CPU usage during waits

**Network**:
- Depends on page size and case count
- Typical: 1-10MB per attorney search
- Consider rate limiting for large batches

---

## 12. Known Limitations & Future Enhancements

### 12.1 Current Limitations

1. **Sequential Case Extraction**: Cases processed one at a time; no parallel extraction
2. **No Incremental Export**: All results exported at end; no streaming export
3. **Fixed Case Type Filter**: Single case type filter; cannot filter multiple types
4. **Limited Error Recovery**: Browser crashes require full restart
5. **Manual Captcha Dependency**: Headless mode requires API key for automation

### 12.2 Planned Enhancements

**Short Term**:
- [ ] Add incremental export option
- [ ] Improve error messages with actionable suggestions
- [ ] Add configuration validation warnings (non-blocking)

**Medium Term**:
- [ ] Parallel case extraction (with rate limiting)
- [ ] Database export option (SQLite/PostgreSQL)
- [ ] Web dashboard for monitoring and configuration
- [ ] Retry mechanism for failed case extractions

**Long Term**:
- [ ] Machine learning for case relevance scoring
- [ ] Automatic selector update mechanism
- [ ] Distributed execution support
- [ ] API endpoint for remote execution and web application

### 12.3 Maintenance Considerations

**Selector Updates**:
- Portal UI changes may require selector updates
- Use `inspect_website.py` to discover new selectors
- Maintain fallback selector lists

**Browser Updates**:
- Chrome updates may affect user agent extraction
- Playwright updates may require code changes
- Test after major browser updates

**API Changes**:
- 2Captcha API changes may require handler updates
- Monitor API documentation for deprecations

---

## Appendix A: Code Examples

### Example: Adding a New Attorney

```python
# In config.py
ATTORNEYS = [
    {"first_name": "JOHN", "last_name": "DOE"},
    {"first_name": "JANE", "last_name": "SMITH"},  # Add new attorney
]
```

### Example: Custom Export Format

```python
# In result_exporter.py, add new function
def export_custom_format(df, output_dir, timestamp):
    # Custom export logic
    pass

# In export_results(), add format check
if OUTPUT_FORMAT.lower() == "custom":
    export_custom_format(df, output_dir, timestamp)
```

### Example: Adding a New Charge Keyword

```python
# In config.py
CHARGE_KEYWORDS = [
    "ASSAULT",
    "THEFT",      # Add new keyword
    "BURGLARY",   # Add new keyword
]
```

---

## Appendix B: Glossary

- **Attorney**: Legal representative whose cases are being searched
- **Case Type**: Category of legal case (e.g., FELONY, MISDEMEANOR)
- **Charge Keyword**: Search term used to filter case descriptions
- **Stealth**: Techniques to prevent bot detection
- **User Agent**: Browser identification string
- **Thread Pool**: Collection of worker threads for concurrent execution
- **Selector**: CSS/XPath expression to locate DOM elements

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-27  
**Maintainer**: Development Team

For questions or contributions, please refer to the project repository.
