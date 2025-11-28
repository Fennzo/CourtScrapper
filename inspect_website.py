"""
Website inspection script to identify element selectors - Using Playwright
This script will navigate to the website and help identify the correct selectors
"""
import time
import logging
from config import BASE_URL
from utils import setup_browser

logger = logging.getLogger(__name__)

# Removed: browser setup functions moved to utils.py for reusability across the project


# Print a quick inventory of inputs, selects, buttons, links, and tables on the page.
def inspect_page(page, page_name):
    logger.info(f"\n{'='*60}")
    logger.info(f"Inspecting: {page_name}")
    logger.info(f"{'='*60}")
    
    # Get page title
    logger.info(f"Page Title: {page.title()}")
    logger.info(f"Current URL: {page.url}")
    
    # Find all input fields
    logger.info("\n--- Input Fields ---")
    inputs = page.locator("input").all()
    for i, inp in enumerate(inputs[:10]):  # Limit to first 10
        name = inp.get_attribute("name") or ""
        inp_id = inp.get_attribute("id") or ""
        inp_type = inp.get_attribute("type") or ""
        placeholder = inp.get_attribute("placeholder") or ""
        logger.info(f"Input {i+1}: name='{name}', id='{inp_id}', type='{inp_type}', placeholder='{placeholder}'")
    
    # Find all select dropdowns
    logger.info("\n--- Select Dropdowns ---")
    selects = page.locator("select").all()
    for i, sel in enumerate(selects):
        name = sel.get_attribute("name") or ""
        sel_id = sel.get_attribute("id") or ""
        logger.info(f"Select {i+1}: name='{name}', id='{sel_id}'")
        options = sel.locator("option").all()
        logger.info(f"  Options ({len(options)}):")
        for opt in options[:5]:  # Show first 5 options
            text = opt.text_content() or ""
            logger.info(f"    - {text}")
    
    # Find all buttons
    logger.info("\n--- Buttons ---")
    buttons = page.locator("button").all()
    for i, btn in enumerate(buttons[:10]):
        btn_text = btn.text_content() or ""
        btn_id = btn.get_attribute("id") or ""
        btn_class = btn.get_attribute("class") or ""
        logger.info(f"Button {i+1}: text='{btn_text.strip()[:50]}', id='{btn_id}', class='{btn_class}'")
    
    # Find all links
    logger.info("\n--- Links (first 10) ---")
    links = page.locator("a").all()
    for i, link in enumerate(links[:10]):
        link_text = link.text_content() or ""
        href = link.get_attribute("href") or ""
        logger.info(f"Link {i+1}: text='{link_text.strip()[:50]}', href='{href[:80]}'")
    
    # Find tables
    logger.info("\n--- Tables ---")
    tables = page.locator("table").all()
    logger.info(f"Found {len(tables)} table(s)")
    for i, table in enumerate(tables):
        rows = table.locator("tr").all()
        logger.info(f"  Table {i+1}: {len(rows)} rows")
        if rows:
            cols = rows[0].locator("td, th").all()
            logger.info(f"    Columns: {len(cols)}")
            if cols:
                header_texts = [col.text_content() or "" for col in cols[:5]]
                logger.info(f"    Header: {[text.strip()[:30] for text in header_texts]}")

# Entry point for the inspection helper: navigates, logs, and keeps the page open.
def main():
    # Set up logging only when run as standalone script
    from utils import setup_logging
    setup_logging()
    
    # Use shared browser setup with stealth features (non-headless for inspection)
    playwright, browser, context, page = setup_browser(headless=False)
    
    try:
        logger.info("Navigating to website...")
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(5)
        
        # Inspect initial page
        inspect_page(page, "Initial Search Page")
        
        # Try to find and expand advanced options
        logger.info("\n\nTrying to find 'Advanced Filtering Options'...")
        advanced_selectors = [
            "text=Advanced Filtering Options",
            "a:has-text('Advanced')",
            "button:has-text('Advanced')"
        ]
        
        for selector in advanced_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=5000):
                    logger.info(f"Found element with selector: {selector}")
                    tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                    text = element.text_content() or ""
                    logger.info(f"  Tag: {tag_name}")
                    logger.info(f"  Text: {text.strip()[:100]}")
                    logger.info(f"  Clicking to expand...")
                    element.click()
                    time.sleep(3)
                    inspect_page(page, "After Expanding Advanced Options")
                    break
            except Exception as e:
                logger.warning(f"  Not found with {selector}: {e}")
        
        logger.info("\n\nInspection complete! Browser will stay open for 30 seconds...")
        logger.info("You can manually interact with the page to verify selectors.")
        time.sleep(30)
        
    except Exception as e:
        logger.error(f"Error during inspection: {e}")
    finally:
        input("Press Enter to close the browser...")
        # page.close()
        # context.close()
        # browser.close()
        # playwright.stop()

if __name__ == "__main__":
    main()
