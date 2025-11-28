"""
Main entry point for Dallas County Scraper
"""
from utils import setup_logging, validate_config, display_config
from scraper_pool import run_all_attorneys_concurrent
from result_exporter import export_results
from config import OUTPUT_DIR, ATTORNEYS

# Main entry point - orchestrates configuration validation, scraping, and export.
def main():

    logger = setup_logging()
    
    # Log header
    logger.info("Dallas County Courts Portal Scraper")
    logger.info("=" * 50)
    
    # Validate configuration
    is_valid, error_message = validate_config()
    if not is_valid:
        logger.error(error_message)
        return
    
    # Display configuration
    display_config()
    logger.info("=" * 50)
    
    try:
        # Run scraping for all attorneys concurrently using thread pool
        logger.info(f"Starting concurrent scraping for {len(ATTORNEYS)} attorney(s)...")
        results = run_all_attorneys_concurrent(ATTORNEYS)
        
        # Export results
        if results:
            export_results(results, OUTPUT_DIR)
        else:
            logger.warning("No matching cases found")
    
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
        logger.info("Partial results may be available in logs")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()

