"""
Thread pool manager for concurrent attorney scraping.
Handles ThreadPoolExecutor and manages multiple scraper instances.
"""
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from scraper import DallasCountyScraper

logger = logging.getLogger(__name__)

# Maximum number of worker threads in the pool.
# Defaults to 32 or can be overridden via MAX_WORKERS environment variable.
# For I/O-bound tasks like web scraping, a higher multiplier of CPU count is reasonable.
# If not set via env var, defaults to max(32, os.cpu_count() * 4) for I/O-bound operations
DEFAULT_MAX_WORKERS = int(os.getenv("MAX_WORKERS", max(32, (os.cpu_count() or 4) * 4)))


# Worker function executed by ThreadPoolExecutor for a single attorney.
# Creates a scraper instance, runs scraping, and returns results.
# Args:
#     attorney: Attorney dict with 'first_name' and 'last_name'
#     attorney_index: Index of the attorney for logging
# Returns:
#     tuple: (attorney_index, results, success, error)
def scrape_attorney_worker(attorney, attorney_index):
    thread_name = f"Worker-{attorney_index}"
    
    # Validate attorney parameter before use
    if not isinstance(attorney, dict):
        error_msg = f"{thread_name} validation failed: attorney must be a dict, got {type(attorney).__name__}"
        logger.error(error_msg)
        return (attorney_index, [], False, ValueError(error_msg))
    
    if 'first_name' not in attorney or 'last_name' not in attorney:
        missing_keys = [k for k in ['first_name', 'last_name'] if k not in attorney]
        error_msg = f"{thread_name} validation failed: attorney dict missing required keys: {missing_keys}"
        logger.error(error_msg)
        return (attorney_index, [], False, ValueError(error_msg))
    
    # Extract validated values for use throughout the function
    first_name = attorney.get('first_name', '')
    last_name = attorney.get('last_name', '')
    
    if not first_name or not last_name:
        error_msg = f"{thread_name} validation failed: first_name and last_name cannot be empty"
        logger.error(error_msg)
        return (attorney_index, [], False, ValueError(error_msg))
    
    logger.info(f"{thread_name} starting for attorney: {first_name} {last_name}")
    
    scraper = None
    try:
        # Create scraper instance for this attorney
        scraper = DallasCountyScraper(attorney)
        
        # Run scraping for this attorney
        success = scraper.run()
        
        if success:
            # Get results from this scraper
            attorney_results = scraper.get_results()
            
            logger.info(
                f"{thread_name} completed: Found {len(attorney_results)} case(s) "
                f"for {first_name} {last_name}"
            )
            return (attorney_index, attorney_results, True, None)
        else:
            logger.warning(f"{thread_name} failed for attorney: {first_name} {last_name}")
            return (attorney_index, [], False, None)
    
    except Exception as e:
        logger.error(f"{thread_name} error: {e}", exc_info=True)
        return (attorney_index, [], False, e)
    
    finally:
        # Cleanup scraper resources
        if scraper is not None and hasattr(scraper, 'cleanup'):
            scraper.cleanup()
        
        logger.info(f"{thread_name} finished")


# Run scraping for all attorneys concurrently using ThreadPoolExecutor.
# Each attorney gets its own scraper instance with its own browser.
# Args:
#     attorneys: List of attorney dicts with 'first_name' and 'last_name'
# Returns:
#     list: Aggregated results from all attorneys
def run_all_attorneys_concurrent(attorneys):
    if not attorneys or len(attorneys) == 0:
        logger.warning("No attorneys to process")
        return []
    
    # Thread-safe result collection
    shared_results = []
    results_lock = threading.Lock()
    thread_exceptions = []
    
    try:
        # Cap the number of workers to prevent excessive thread creation
        num_workers = min(len(attorneys), DEFAULT_MAX_WORKERS)
        
        # Use ThreadPoolExecutor to manage worker threads
        logger.info(
            f"\nStarting ThreadPoolExecutor with {num_workers} worker(s) "
            f"(capped from {len(attorneys)} attorney(s), max_workers={DEFAULT_MAX_WORKERS})..."
        )
        
        with ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="ScraperWorker") as executor:
            # Submit all attorney scraping tasks to the thread pool
            future_to_attorney = {
                executor.submit(scrape_attorney_worker, attorney, idx): (idx, attorney)
                for idx, attorney in enumerate(attorneys)
            }
            
            logger.info(f"Submitted {len(future_to_attorney)} task(s) to thread pool")
            if len(attorneys) > num_workers:
                logger.info(
                    f"Note: {len(attorneys) - num_workers} task(s) will be queued "
                    f"and processed as worker threads become available"
                )
            
            # Process completed tasks as they finish
            for future in as_completed(future_to_attorney):
                attorney_index, attorney = future_to_attorney[future]
                try:
                    idx, results, success, error = future.result()
                    
                    # Thread-safely append results
                    if results:
                        with results_lock:
                            shared_results.extend(results)
                    
                    # Track exceptions
                    if error:
                        thread_exceptions.append((f"Worker-{idx}", error))
                
                except Exception as e:
                    logger.error(f"Error processing future for attorney {attorney_index}: {e}")
                    thread_exceptions.append((f"Worker-{attorney_index}", e))
        
        logger.info("All worker threads completed")
        
        # Check for exceptions
        if thread_exceptions:
            logger.warning(f"{len(thread_exceptions)} worker(s) encountered errors:")
            for worker_name, error in thread_exceptions:
                logger.warning(f"  - {worker_name}: {error}")
        
        # Show breakdown by attorney
        if shared_results:
            from collections import Counter
            attorney_counts = Counter([r.get('attorney_name', 'UNKNOWN') for r in shared_results])
            logger.info("\nCases found per attorney:")
            for attorney_name, count in attorney_counts.items():
                logger.info(f"  - {attorney_name}: {count} case(s)")
        
        logger.info(f"\nTotal cases extracted: {len(shared_results)}")
        return shared_results
        
    except Exception as e:
        logger.error(f"Error in run_all_attorneys_concurrent: {e}")
        return []

