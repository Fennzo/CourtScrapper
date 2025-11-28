[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-1.56+-green.svg)](https://playwright.dev/)

An automated web scraping tool designed to extract case information from the Dallas County Courts Portal. This tool enables legal professionals, researchers, and investigators to efficiently search and collect case data for multiple attorneys simultaneously with advanced filtering capabilities.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output](#output)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [License](#license)

---

## 🎯 Overview

The Dallas County Courts Portal Scraper automates the process of searching for and extracting case information from the public Dallas County Courts Portal. It eliminates the need for manual case-by-case searches by:

- **Searching multiple attorneys concurrently** using a thread pool for efficient processing
- **Filtering results** by case type, charge keywords, and date range
- **Handling captchas automatically** via 2Captcha API or manual completion
- **Exporting structured data** in multiple formats (Excel, CSV, JSON) with professional formatting

This tool is designed for legal professionals who need to systematically track cases across multiple attorneys, filter by specific charge types, and export data for analysis or reporting.

---

## ✨ Features

### Core Capabilities

- **Multi-Attorney Support**: Process multiple attorneys concurrently with thread pool execution
- **Intelligent Filtering**: 
  - Filter by case type (default: felony cases)
  - Filter by charge keywords (e.g., "ASSAULT", "THEFT")
  - Filter by minimum file date/year
- **Captcha Handling**: 
  - Automated solving via 2Captcha API
  - Manual completion fallback for reliability
- **Stealth Automation**: Browser automation with anti-detection measures to mimic human behavior
- **Flexible Export**: 
  - Excel format with multi-sheet support (one sheet per attorney)
  - CSV format for data analysis
  - JSON format for programmatic access
- **Robust Error Handling**: 
  - Session recovery on navigation failures
  - Partial result preservation on interruption
  - Comprehensive logging for debugging

### Technical Features

- **Concurrent Processing**: Uses ThreadPoolExecutor to process multiple attorneys simultaneously
- **Browser Automation**: Built on Playwright for fast, reliable browser control
- **Data Extraction**: Extracts comprehensive case details including:
  - Case number, file date, judicial officer
  - Case status and type
  - Charge descriptions
  - Bond amounts
  - Disposition and sentencing information
- **Thread-Safe Operations**: Safe concurrent execution with proper resource management

---

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8 or higher** ([Download Python](https://www.python.org/downloads/))
- **Google Chrome** or **Chromium** browser (automatically installed with Playwright)
- **Git** (optional, for cloning the repository)

### System Requirements

- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 4GB RAM (8GB+ recommended for concurrent processing)
- **Internet Connection**: Required for accessing the Dallas County Courts Portal

---

## 🚀 Installation

### Step 1: Clone or Download

If using Git:
```bash
git clone <repository-url>
cd DallasCountyScraper
```

Or download and extract the ZIP file to your desired location.

### Step 2: Install Python Dependencies

Navigate to the project directory and install required packages:

```bash
pip install -r requirements.txt
```

**Note**: It's recommended to use a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Install Playwright Browsers

Install the Chromium browser used by Playwright:

```bash
playwright install chromium
```

This step downloads the browser binary (~170MB). Playwright handles browser updates automatically.

### Step 4: Configure the Scraper

Edit `config.py` with your search criteria (see [Configuration](#configuration) section for details).

---

## ⚡ Quick Start

1. **Configure attorneys and keywords** in `config.py`:
   ```python
   ATTORNEYS = [
       {"first_name": "JOHN", "last_name": "DOE"},
   ]
   CHARGE_KEYWORDS = ["ASSAULT", "THEFT"]
   ```

2. **Run the scraper**:
   ```bash
   python main.py
   ```

3. **Find results** in the `results/` directory (Excel file with timestamp)

That's it! The scraper will automatically:
- Navigate to the portal
- Search for each attorney
- Filter cases by your criteria
- Extract case details
- Export results to Excel

---

## ⚙️ Configuration

All configuration is managed through `config.py` with optional environment variable overrides via a `.env` file.

### Required Configuration

#### 1. Attorneys List
Define the attorneys to search for:

```python
ATTORNEYS = [
    {"first_name": "JOHN", "last_name": "DOE"},
    {"first_name": "JANE", "last_name": "SMITH"},
    # Add more attorneys as needed
]
```

**Important**: Names must match exactly as they appear in the portal (case-sensitive).

#### 2. Charge Keywords
Specify keywords to filter case descriptions:

```python
CHARGE_KEYWORDS = [
    "ASSAULT",
    "THEFT",
    "BURGLARY",
    # Add more keywords as needed
]
```

Cases matching **ANY** of these keywords will be included in the results.

### Optional Configuration

#### Date Filtering
Set the minimum year for cases to process:

**Option 1**: Edit `config.py`
```python
MINIMUM_CASE_YEAR = 2024
```

**Option 2**: Use environment variable (recommended for deployment)
Create a `.env` file:
```env
MINIMUM_CASE_YEAR=2024
```

#### Captcha Service (Optional but Recommended)

For automated captcha solving, set up 2Captcha:

1. **Get API Key**: Sign up at [2captcha.com](https://2captcha.com)
2. **Configure**: Add to `.env` file:
   ```env
   CAPTCHA_API_KEY=your_api_key_here
   ```
3. **Enable**: In `config.py`:
   ```python
   USE_CAPTCHA_SERVICE = True
   ```

**Note**: Without an API key, the scraper will pause for manual captcha completion. This is fine for testing but impractical for automation.

#### Browser Settings

```python
# Run browser in background (no visible window)
HEADLESS = True  # Set to False for debugging

# Chrome executable path (if Chrome is installed in non-standard location)
# Configure via environment variable: CHROME_PATH=/path/to/chrome
```

#### Output Settings

```python
# Output directory
OUTPUT_DIR = "results"

# Output format: "excel", "csv", or "json"
OUTPUT_FORMAT = "excel"
```

#### Advanced Settings

```python
# Delay before browser actions (useful for debugging)
ACTION_DELAY_SECONDS = 0  # Set to 0 for normal operation, 3+ for manual observation

# Case type filter (default: "FELONY")
CASE_TYPE = "FELONY"

# Enable automatic session recovery on errors
ENABLE_SESSION_RECOVERY = True
```

### Environment Variables

Create a `.env` file in the project root to override config values:

```env
# Captcha API Key
CAPTCHA_API_KEY=your_2captcha_api_key_here

# Chrome Path (if non-standard location)
CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe

# Minimum Case Year
MINIMUM_CASE_YEAR=2024

# Thread Pool Workers (optional, defaults to max(32, CPU_COUNT * 4))
MAX_WORKERS=16
```

---

## 📖 Usage

### Basic Usage

Run the scraper with default settings:

```bash
python main.py
```

The scraper will:
1. Validate your configuration
2. Display the configuration summary
3. Process each attorney concurrently
4. Export results to `results/` directory
5. Display summary statistics

### Output

Results are saved in the `results/` directory with the following naming convention:

- **Excel**: `cases_YYYYMMDD_HHMMSS.xlsx`
- **CSV**: `cases_YYYYMMDD_HHMMSS.csv`
- **JSON**: `cases_YYYYMMDD_HHMMSS.json`

#### Excel Export Features

- **Multi-Sheet Support**: One sheet per attorney plus an "All Cases" summary sheet
- **Professional Formatting**: 
  - Auto-sized columns
  - Styled headers (blue background, white text)
  - Proper column ordering
- **Column Titles**: User-friendly column names (e.g., "Attorney", "Case Number", "File Date")

### Logging

All operations are logged to `logs/scraper_YYYYMMDD_HHMMSS.log` with:
- Thread identification for concurrent execution
- Detailed progress information
- Error messages and stack traces
- Configuration summary

Review logs for debugging or audit purposes.

### Interrupting Execution

Press `Ctrl+C` to gracefully interrupt the scraper. Partial results will be exported automatically.

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue: "No matching cases found"

**Possible Causes:**
- Attorney names don't match portal exactly (check case sensitivity)
- No cases match the charge keywords
- All cases are before the minimum year threshold
- Case type filter doesn't match (default is "FELONY")

**Solutions:**
- Verify attorney names match the portal exactly
- Check charge keywords are spelled correctly
- Adjust `MINIMUM_CASE_YEAR` if needed
- Review logs for detailed filtering information

#### Issue: Captcha not solving automatically

**Solutions:**
- Verify `CAPTCHA_API_KEY` is set correctly in `.env`
- Check 2Captcha account balance at [2captcha.com](https://2captcha.com)
- Set `USE_CAPTCHA_SERVICE = False` to use manual completion for testing

#### Issue: Chrome not found

**Solutions:**
- Ensure Chrome is installed on your system
- Set `CHROME_PATH` environment variable to Chrome executable location
- For Windows: Default is `C:\Program Files\Google\Chrome\Application\chrome.exe`
- For Linux: Try `/usr/bin/google-chrome` or `/usr/bin/chromium-browser`
- For macOS: Try `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`

#### Issue: "Latest case is not from [YEAR]" error

**Solutions:**
- The attorney has no cases from the specified minimum year
- Adjust `MINIMUM_CASE_YEAR` in config or `.env` file
- Verify the attorney has recent cases in the portal

#### Issue: Timeout errors

**Solutions:**
- Increase `EXPLICIT_WAIT` or `PAGE_LOAD_TIMEOUT` in `config.py`
- Check your internet connection
- The portal may be experiencing high traffic

#### Issue: Browser crashes or errors

**Solutions:**
- Ensure sufficient memory is available (close other applications)
- Reduce `MAX_WORKERS` environment variable for fewer concurrent browsers
- Enable `ENABLE_SESSION_RECOVERY = True` for automatic recovery
- Check logs for specific error messages

### Getting Help

1. **Check the logs**: Review `logs/` directory for detailed error information
2. **Review configuration**: Verify all settings in `config.py`
3. **Test with single attorney**: Start with one attorney to isolate issues
4. **Check documentation**: See `docs/TECHNICAL_DOCUMENTATION.md` for architecture details

---

## 📁 Project Structure

```
DallasCountyScraper/
│
├── main.py                 # Application entry point
├── config.py               # Configuration file
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── scraper.py             # Core scraper class
├── scraper_pool.py        # Thread pool manager for concurrent execution
├── case_data_extractor.py # Case detail extraction functions
├── captcha_handler.py     # Captcha detection and solving
├── result_exporter.py     # Export to CSV/Excel/JSON
├── utils.py               # Browser setup and utility functions
├── inspect_website.py     # Standalone website inspection tool
│
├── docs/
│   ├── TECHNICAL_DOCUMENTATION.md  # Detailed technical documentation
│   └── FLOW_DIAGRAM.md             # Visual process flow
│
├── logs/                  # Execution logs (auto-generated)
├── results/               # Exported results (auto-generated)
└── .env                   # Environment variables (create this file)
```

### Key Modules

- **`main.py`**: Orchestrates the entire workflow
- **`scraper.py`**: Handles browser automation and case extraction per attorney
- **`scraper_pool.py`**: Manages concurrent execution across multiple attorneys
- **`case_data_extractor.py`**: Extracts structured data from case detail pages
- **`captcha_handler.py`**: Handles reCAPTCHA detection and solving
- **`result_exporter.py`**: Formats and exports results to various formats

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help improve this project:

### Reporting Issues

If you encounter a bug or have a feature request:

1. Check existing issues to avoid duplicates
2. Create a new issue with:
   - Clear description of the problem or feature
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
   - System information (OS, Python version, etc.)

### Submitting Changes

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** with clear, documented code
4. **Test your changes** thoroughly
5. **Commit with descriptive messages**: `git commit -m "Add feature: description"`
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Open a Pull Request** with:
   - Description of changes
   - Reason for the change
   - Any breaking changes

### Code Style

- Follow PEP 8 Python style guidelines
- Add docstrings to all functions and classes
- Include comments for complex logic
- Maintain existing code style and structure

### Areas for Contribution

- Bug fixes and error handling improvements
- Performance optimizations
- Additional export formats
- Enhanced filtering capabilities
- Documentation improvements
- Test coverage

---

## 📚 Documentation

### Additional Documentation

For detailed technical information, refer to:

- **[Technical Documentation](docs/TECHNICAL_DOCUMENTATION.md)**: Comprehensive architecture overview, module reference, design patterns, and API specifications
- **[Flow Diagram](docs/FLOW_DIAGRAM.md)**: Visual representation of the scraping process flow

### Key Concepts

**Case Type Filtering**: Only processes rows containing the configured case type (default: "FELONY"). This is a substring match, so it's case-insensitive.

**Charge Keyword Filtering**: On each case detail page, checks if any of the configured keywords appear in the page content. If no keywords match, the case is skipped entirely.

**Date Filtering**: Before processing any cases, validates that the newest case in the results meets the minimum year requirement. This prevents processing for attorneys who haven't practiced recently in Dallas County.
**Concurrent Processing**: Uses Python's ThreadPoolExecutor to run multiple scraper instances simultaneously, each with its own browser context. This significantly improves throughput for multi-attorney searches.

---

## ⚖️ License

**Note**: This tool is designed for legitimate use cases such as legal research, case tracking, and public record access. Users are responsible for complying with the Dallas County Courts Portal's terms of service and applicable laws regarding web scraping and data collection.

---

## 🙏 Acknowledgments

- **Playwright**: Fast and reliable browser automation
- **2Captcha**: Captcha solving service integration
- **pandas & openpyxl**: Data processing and Excel export capabilities

---

## 📊 Project Status

**Status**: ✅ Active Development / Production Ready

### Current Version
- Multi-attorney concurrent processing
- Automated captcha solving
- Excel/CSV/JSON export with formatting
- Session recovery and error handling

### Known Limitations

- Sequential case extraction (cases processed one at a time)
- Chrome/Chromium browser only (Firefox/Edge support not implemented)

### Roadmap

**Planned Enhancements:**
- [ ] Parallel case extraction
- [ ] Database export option (SQLite/PostgreSQL)
- [ ] Enhanced error messages with actionable suggestions
- [ ] Web dashboard for monitoring and configuration

See `docs/TECHNICAL_DOCUMENTATION.md` for detailed roadmap information.

---

## 📞 Support

For questions, issues, or contributions:

- **Issues**: Open an issue on the repository
- **Documentation**: Check `docs/TECHNICAL_DOCUMENTATION.md` for technical details
- **Logs**: Review `logs/` directory for execution traces and debugging information

---

**Made with ❤️ for legal professionals and researchers**

*Last Updated: November 2025*
