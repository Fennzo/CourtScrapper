"""
Data extraction functions for case details - Using Playwright
"""
import time
import logging
import re
import json
from datetime import datetime
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

# List of words that disqualify an amount from being extracted as a bond amount
BOND_AMOUNT_DISQUALIFIERS = (
    "due",
    "owed",
    "balance",
    "paid",
    "fee",
    "fees",
    "financial",
    "assessment",
    "assessments",
    "transaction",
    "transactions",
    "credit",
    "credits",
    "payment",
    "payments",
    "total",
    "fine",
    "fines",
    "cost",
    "costs"
)


# Raised when an expected field cannot be extracted.
class FieldExtractionError(Exception):
    pass


# Ensure required fields are present, logging success/failure.
def ensure_field_extracted(field_label, value, required=True):
    if isinstance(value, str):
        value = value.strip()
    if value:
        logger.info(f"{field_label} extracted: {value}")
        return value
    if required:
        raise FieldExtractionError(f"{field_label} could not be extracted")
    logger.info(f"{field_label} not present on the page")
    return ""

# Attempt a field extraction and capture missing-field errors.
def record_field_extraction(field_label, value, field_errors, required=True):
    try:
        return ensure_field_extracted(field_label, value, required=required)
    except FieldExtractionError as exc:
        field_errors.append(field_label)
        logger.exception(exc)
        return ""

# Split a section's text into trimmed non-empty lines.
def normalize_section_lines(section_text):
    if not section_text:
        return []
    return [line.strip() for line in section_text.splitlines() if line.strip()]

# Pull the value that follows a specific label inside a line list.
def extract_value_from_lines(lines, label):
    if not lines:
        return ""
    label_lower = label.lower()
    pattern = re.compile(rf"^{re.escape(label)}\s*:?\s*(.+)$", re.IGNORECASE)
    for idx, line in enumerate(lines):
        if line.lower() == label_lower and idx + 1 < len(lines):
            return lines[idx + 1].strip()
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return ""

# Grab the text content for a card/section anchored by a heading label.
def get_section_text(page, heading_text):
    normalized = heading_text.lower()
    heading_locator = page.locator(
        f"xpath=//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::div or self::p]"
        f"[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{normalized}')]"
    ).first
    try:
        heading_locator.wait_for(state="visible", timeout=2000)
        section_text = heading_locator.evaluate(
            """el => {
                const candidates = [
                    el.closest('section'),
                    el.closest('.card'),
                    el.closest('.panel'),
                    el.closest('.MuiPaper-root'),
                    el.parentElement
                ];
                for (const candidate of candidates) {
                    if (candidate && candidate.innerText && candidate.innerText.trim().length > 0) {
                        return candidate.innerText;
                    }
                }
                return el.innerText || '';
            }"""
        )
        return section_text or ""
    except PlaywrightTimeoutError:
        return ""
    except Exception as exc:
        logger.debug(f"Unable to capture text for section '{heading_text}': {exc}")
        return ""

# Find the text associated with a label element or its siblings.
def get_text_from_label_element(element):
    try:
        element.wait_for(state="visible", timeout=2000)
    except PlaywrightTimeoutError:
        return ""
    try:
        parent = element.locator("..").first
        sibling = parent.locator("+ *").first
        if sibling and sibling.is_visible(timeout=500):
            sibling_text = sibling.text_content() or ""
            if sibling_text.strip():
                return sibling_text.strip()
    except Exception:
        pass
    try:
        sibling = element.locator("xpath=following-sibling::*[1]").first
        if sibling and sibling.is_visible(timeout=500):
            sibling_text = sibling.text_content() or ""
            if sibling_text.strip():
                return sibling_text.strip()
    except Exception:
        pass
    element_text = element.text_content() or ""
    return element_text.strip()

# Iterate through selectors until a visible value is discovered.
def extract_value_by_selectors(page, selectors, regex=None, treat_text_selectors_as_labels=True):
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if not element:
                continue
            use_label_logic = treat_text_selectors_as_labels and (
                selector.startswith("text=") or ":has-text" in selector
            )
            if use_label_logic:
                text = get_text_from_label_element(element)
            else:
                if not element.is_visible(timeout=2000):
                    continue
                text = element.text_content() or ""
            if not text:
                continue
            text = text.strip()
            if regex:
                match = re.search(regex, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            else:
                return text
        except PlaywrightTimeoutError:
            continue
        except Exception as exc:
            logger.debug(f"Selector '{selector}' failed during extraction: {exc}")
            continue
    return ""


# Build a structured dict of case metadata from the open detail page.
def extract_case_details(page):
    case_data = {
        "case_number": "",
        "file_date": "",
        "judicial_officer": "",
        "case_status": "",
        "case_type": "",
        "charge_description": "",
        "bond_amount": "",
        "disposition": "",
        "sentencing_info": ""
    }
    field_errors = []
    
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
        time.sleep(2)
        
        case_info_lines = normalize_section_lines(get_section_text(page, "Case Information"))
        
        # Case number
        case_number_selectors = [
            "text=Case Number",
            "text=Case #",
            "[id*='case'][id*='number']",
            "[class*='case-number']",
            "td:has-text('Case Number') + td",
            "th:has-text('Case Number') + td"
        ]
        case_data["case_number"] = extract_value_from_lines(case_info_lines, "Case Number") or extract_value_by_selectors(
            page,
            case_number_selectors,
            regex=r'Case\s*(?:Number|#)?:?\s*([A-Z0-9-]+)'
        )
        case_data["case_number"] = record_field_extraction("Case Number", case_data["case_number"], field_errors)
        
        # File date
        date_selectors = [
            "text=File Date",
            "text=Filed",
            "[id*='file'][id*='date']",
            "td:has-text('File Date') + td",
            "th:has-text('File Date') + td"
        ]
        case_data["file_date"] = extract_value_from_lines(case_info_lines, "File Date") or extract_value_by_selectors(
            page,
            date_selectors
        )
        case_data["file_date"] = record_field_extraction("File Date", case_data["file_date"], field_errors)
        
        # Judicial officer
        officer_selectors = [
            "text=Judicial Officer",
            "text=Judge",
            "[id*='judge'], [id*='officer']",
            "td:has-text('Judicial Officer') + td",
            "th:has-text('Judicial Officer') + td"
        ]
        case_data["judicial_officer"] = extract_value_from_lines(case_info_lines, "Judicial Officer") or extract_value_by_selectors(
            page,
            officer_selectors
        )
        case_data["judicial_officer"] = record_field_extraction("Judicial Officer", case_data["judicial_officer"], field_errors)
        
        # Case status
        case_status_selectors = [
            "text=Case Status",
            "[class*='case-status']",
            "[id*='case-status']",
            "td:has-text('Case Status') + td",
            "th:has-text('Case Status') + td"
        ]
        case_data["case_status"] = extract_value_from_lines(case_info_lines, "Case Status") or extract_value_by_selectors(
            page,
            case_status_selectors
        )
        case_data["case_status"] = record_field_extraction("Case Status", case_data["case_status"], field_errors)
        
        # Case type (optional for reporting context)
        case_type_selectors = [
            "text=Case Type",
            "text=Description",
            "[id*='case-type']",
            "td:has-text('Case Type') + td"
        ]
        case_data["case_type"] = extract_value_from_lines(case_info_lines, "Case Type") or extract_value_by_selectors(
            page,
            case_type_selectors
        )
        case_data["case_type"] = record_field_extraction("Case Type", case_data["case_type"], field_errors, required=False)
        
        # Charge description
        case_data["charge_description"] = extract_charge_description(page)
        case_data["charge_description"] = record_field_extraction("Charge Description", case_data["charge_description"], field_errors)
        
        # Bond amount
        case_data["bond_amount"] = extract_bond_amount(page)
        case_data["bond_amount"] = record_field_extraction("Bond Amount", case_data["bond_amount"], field_errors)
        
        # Disposition / sentencing info (only for ACTIVE/OPEN cases)
        disposition_value = "NA"
        confinement_and_probation_value = "NA"
        case_status_value = (case_data.get("case_status") or "").strip().upper()
        if case_status_value in ("ACTIVE", "OPEN"):
            logger.info(f"Skipping disposition/sentencing extraction because case status is '{case_status_value}'")
        else:
            disposition_value, confinement_and_probation_value = extract_disposition_and_sentencing(page)
            if not disposition_value:
                disposition_value = "NA"
            if not confinement_and_probation_value:
                confinement_and_probation_value = "NA"

        case_data["disposition"] = record_field_extraction(
            "Disposition",
            disposition_value,
            field_errors,
            required=False
        )
        case_data["sentencing_info"] = record_field_extraction(
            "Disposition / Sentencing",
            confinement_and_probation_value,
            field_errors,
            required=False
        )
        
    except Exception as e:
        logger.error(f"Error extracting case details: {e}")
    
    logger.info(f"Case data snapshot: {json.dumps(case_data, ensure_ascii=False)}")
    if field_errors:
        logger.warning(f"Extraction completed with missing fields: {', '.join(field_errors)}")
    
    return case_data



# Read the primary charge description from the charge table/section.
def extract_charge_description(page):
    try:
        charge_span = page.locator("span.chargeOffenseDescription").first
        if charge_span.count():
            text = charge_span.get_attribute("title") or charge_span.text_content() or ""
            cleaned = " ".join(text.split())
            if cleaned:
                return cleaned
    except Exception as exc:
        logger.debug(f"Error reading charge description span: {exc}")
    
    try:
        charge_rows = page.locator("table:has(span.chargeOffenseDescription) tr")
        row_count = charge_rows.count()
        
        def extract_description_from_row(row_handle):
            try:
                cells = row_handle.locator("td")
                if cells.count() >= 2:
                    desc_text = cells.nth(1).text_content() or ""
                    return " ".join(desc_text.split())
                row_text = row_handle.text_content() or ""
                return " ".join(row_text.split())
            except Exception:
                return ""
        
        if row_count:
            for idx in range(row_count):
                row = charge_rows.nth(idx)
                description = extract_description_from_row(row)
                if description:
                    return description
    except Exception as exc:
        logger.debug(f"Error reading structured charge table: {exc}")
    
    # Fall back to raw section text parsing if table approach fails.
    charge_text = get_section_text(page, "Charge")
    lines = normalize_section_lines(charge_text)
    if not lines:
        return ""
    
    excluded_tokens = {"charge", "charges", "description", "statute", "level", "date"}
    for idx, line in enumerate(lines):
        lower_line = line.lower()
        if lower_line in excluded_tokens:
            continue
        if line.strip().isdigit() and idx + 1 < len(lines):
            candidate = lines[idx + 1]
            if candidate.lower() not in excluded_tokens:
                return candidate.strip()
        if "," in line:
            continue
    return ""

# Build a concise summary of disposition-adjacent info and return the disposition separately.
def extract_disposition_and_sentencing(page):
    confinement_and_probation_value = []
    disposition_text = ""
    
    try:
        # 1) Disposition events section - capture the textual outcomes shown in the Disposition Events grid
        disposition_text = extract_disposition(page)
        
        # 2) Confinement - capture items like "6 Months, STATE JAIL".
        confinement_text = get_section_text(page, "Confinement")
        if confinement_text:
            confinement_lines = normalize_section_lines(confinement_text)
            confinement_value = parse_confinement_details(confinement_lines)
            if confinement_value:
                confinement_and_probation_value.append(f"Confinement: {confinement_value}")
        
        # 3) Probation / community service - capture duration only.
        probation_text = get_section_text(page, "TX CSCD and Community Service")
        if probation_text:
            probation_lines = normalize_section_lines(probation_text)
            probation_value = parse_probation_details(probation_lines)
            if probation_value:
                confinement_and_probation_value.append(f"Probation: {probation_value}")
    except Exception as exc:
        logger.debug(f"Error building disposition summary: {exc}")
    
    summary_text = " || ".join(confinement_and_probation_value) 
    return disposition_text, summary_text


# Extract the textual outcomes shown in the Disposition Events grid.
def extract_disposition(page):
    try:
        table_selectors = [
            "div[id^='CriminalDispositions'] table tbody tr",
            "p:has-text('Disposition Events') ~ div .k-grid table tbody tr",
            "p:has-text('Disposition Events') ~ div table tbody tr"
        ]

        rows = None
        for selector in table_selectors:
            candidate = page.locator(selector)
            if candidate.count():
                rows = candidate
                break
        
        if not rows or rows.count() == 0:
            return ""
        
        events = []
        for idx in range(rows.count()):
            row = rows.nth(idx)
            text = ""
            
            cells = row.locator("td")
            target_cell = cells.nth(cells.count() - 1) if cells.count() else row
            titled_div = target_cell.locator("div[title]").first
            
            if titled_div.count():
                text = titled_div.get_attribute("title") or titled_div.text_content() or ""
            else:
                text = target_cell.text_content() or row.text_content() or ""
            cleaned = " ".join(text.split())
            if cleaned:
                events.append(cleaned)
            if len(events) >= 4:
                break
        
        return " | ".join(events)
    except Exception as exc:
        logger.error(f"Error extracting disposition events grid: {exc}")
        return ""


# Parse confinement lines to produce "6 Months, STATE JAIL" style data.
def parse_confinement_details(lines):
    if not lines:
        return ""
    
    duration_pattern = re.compile(r"(\d+\s*(?:days|months|years))", re.IGNORECASE)
    facility_labels = [
        "STATE JAIL",
        "COUNTY JAIL",
        "PENITENTIARY",
        "PRISON",
        "JAIL"
    ]
    
    duration = "" 
    facility = ""
    
    # Prioritize lines that explicitly mention a facility keyword.
    prioritized_lines = []
    other_lines = []
    for line in lines:
        lower_line = line.lower()
        if any(label.lower() in lower_line for label in facility_labels):
            prioritized_lines.append(line)
        else:
            other_lines.append(line)
    ordered_lines = prioritized_lines + other_lines
    
    for line in ordered_lines:
        lower_line = line.lower()
        if not duration:
            match = duration_pattern.search(lower_line)
            if match:
                duration = match.group(1).strip().title()
        if not facility:
            for label in facility_labels:
                if label.lower() in lower_line:
                    facility = label
                    break
        if duration and facility:
            break
    
    if duration and facility:
        return f"{duration}, {facility}"
    if duration:
        return duration
    if facility:
        return facility
    return ""


# Parse probation/community service lines and return the duration (e.g., "2 Years").
def parse_probation_details(lines):
    if not lines:
        return ""
    
    duration_pattern = re.compile(r"(\d+\s*(?:days|day|months|month|years|year))", re.IGNORECASE)
    
    priority_lines = []
    other_lines = []
    for line in lines:
        if any(keyword in line.lower() for keyword in ["cscd", "probation", "community service"]):
            priority_lines.append(line)
        else:
            other_lines.append(line)
    ordered_lines = priority_lines + other_lines
    
    for line in ordered_lines:
        match = duration_pattern.search(line)
        if match:
            return match.group(1).strip().title()
    
    # If no explicit duration, look for text like "CSCD 2 Years".
    for line in ordered_lines:
        cleaned = line.strip()
        if cleaned:
            return cleaned
    
    return ""

    
    # Extract bond amount using the following logic:
    # 1. Check Bond section for direct gridcell amount
    # 2. If not found, check Bond Settings section and expand bottom-most setting date
    # 3. Look for either dollar amount or "Hold Without Bond"
    # 4. Return "No bond amount set" if nothing found
def extract_bond_amount(page):

    try:
        # Step 1: Look for Bond section with role="gridcell" containing dollar amount
        logger.info("Step 1: Checking Bond section for gridcell with amount")
        try:
            bond_gridcells = page.locator('td[role="gridcell"]')
            for i in range(bond_gridcells.count()):
                cell_text = bond_gridcells.nth(i).text_content() or ""
                cell_text = cell_text.strip()
                # Check if this contains a dollar amount
                if cell_text.startswith('$') and any(char.isdigit() for char in cell_text):
                    # Make sure it's not a financial/fee related cell by checking context
                    parent_row = bond_gridcells.nth(i).locator('xpath=ancestor::tr[1]')
                    row_text = (parent_row.text_content() or "").lower()
                    
                    # Skip if it's in a disqualified context
                    if not any(disqualifier in row_text for disqualifier in BOND_AMOUNT_DISQUALIFIERS):
                        logger.info(f"Found bond amount in gridcell: {cell_text}")
                        return cell_text
        except Exception as exc:
            logger.debug(f"No bond found in gridcell section: {exc}")
        
        # Step 2: Look for Bond Settings section
        logger.info("Step 2: Checking Bond Settings section")
        bond_settings_section = page.locator('#settingInformationDiv')
        
        if not bond_settings_section.count():
            logger.info("No Bond Settings section found")
            return "No bond amount set"
        
        # Check if "Hold Without Bond" is present in the already-visible content
        hold_without_bond = bond_settings_section.locator('div.tyler-span-2:has-text("Hold Without Bond")')
        if hold_without_bond.count():
            logger.info("Found 'Hold Without Bond' in Bond Settings")
            return "Hold Without Bond"
        
        # Step 3: Find and expand the bottom-most setting date row
        logger.info("Step 3: Looking for expandable bond setting rows")
        bond_settings_grid = page.locator('#BondSettingsGrid')
        
        if not bond_settings_grid.count():
            logger.info("No BondSettingsGrid found")
            return "No bond amount set"
        
        # Find all master rows with expand icons (k-plus or k-minus)
        expand_icons = bond_settings_grid.locator('td.k-hierarchy-cell a.k-icon')
        icon_count = expand_icons.count()
        
        if icon_count == 0:
            logger.info("No expandable rows found in Bond Settings")
            return "No bond amount set"
        
        # Get the last (bottom-most) expand icon
        last_icon = expand_icons.nth(icon_count - 1)
        icon_class = last_icon.get_attribute('class') or ""
        
        # Expand if it's collapsed (has k-plus)
        if 'k-plus' in icon_class:
            logger.info(f"Expanding bottom-most bond setting row (row {icon_count})")
            last_icon.click()
            page.wait_for_timeout(1000)  # Wait for expansion animation
        else:
            logger.info(f"Bottom-most row already expanded")
        
        # Step 4: Look for bond amount in the expanded detail row
        logger.info("Step 4: Extracting bond amount from expanded row")
        
        # First check for "Hold Without Bond" after expansion
        hold_without_bond_expanded = bond_settings_section.locator('div.tyler-span-2:has-text("Hold Without Bond")')
        if hold_without_bond_expanded.count():
            logger.info("Found 'Hold Without Bond' after expansion")
            return "Hold Without Bond"
        
        # Look for dollar amounts in divs with padding-left:30px style
        amount_divs = bond_settings_section.locator('div[style*="padding-left:30px"]')
        
        for i in range(amount_divs.count()):
            div_text = amount_divs.nth(i).text_content() or ""
            div_text = div_text.strip()
            
            # Check if this is a dollar amount (starts with $ and has digits)
            if div_text.startswith('$') and any(char.isdigit() for char in div_text):
                # Additional validation: make sure it's not just "Comment:" text
                if not div_text.lower().startswith('comment'):
                    logger.info(f"Found bond amount in expanded settings: {div_text}")
                    return div_text
        
        logger.info("No bond amount found after checking all sources")
        return "No bond amount set"
        
    except Exception as exc:
        logger.error(f"Error extracting bond amount: {exc}")
        return "No bond amount set"


# Check if any of the charge keywords exist in the page text.
# Args:
#     page: Playwright page object
#     charge_keywords: List of keywords to search for
# Returns:
#     True if any keyword is found, False otherwise
def check_for_charge_keyword(page, charge_keywords):
    try:
        # Get all text from page
        page_text = page.locator("body").text_content() or ""
        page_text_lower = page_text.lower()
        
        # Handle both list and single string for backwards compatibility
        if isinstance(charge_keywords, str):
            charge_keywords = [charge_keywords]
        
        # Check for any charge keyword
        for keyword in charge_keywords:
            if keyword.lower() in page_text_lower:
                logger.info(f"Found '{keyword}' in case details")
                return True
        
        logger.info(f"None of the charge keyword(s) {charge_keywords} found in case")
        return False
    except Exception as e:
        logger.error(f"Error checking for charge keyword(s): {e}")
        return False

