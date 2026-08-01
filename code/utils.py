import re
import logging
import time
from functools import wraps
from urllib.parse import urlparse

# Set up logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("NotificationRouter")

def get_logger(name):
    return logging.getLogger(name)

def retry_api(max_retries=3, delay=1.0, backoff=2.0):
    """Decorator to retry API calls on transient failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            t_delay = delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to execute {func.__name__} after {max_retries} attempts: {e}")
                        raise e
                    logger.warning(f"Error executing {func.__name__}: {e}. Retrying in {t_delay:.1f}s...")
                    time.sleep(t_delay)
                    t_delay *= backoff
            return None
        return wrapper
    return decorator

def extract_domains(text):
    """Safely extract domains from actual URLs (e.g. http:// or https://, or words that end with common TLDs like .com, .in, .net)."""
    if not text:
        return []
    
    # Simple regex to find URLs or potential domain names starting with http or ending with standard extensions
    url_pattern = re.compile(
        r'(?:https?://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(?:/[^\s]*)?'
    )
    
    candidates = url_pattern.findall(text)
    domains = []
    
    for cand in candidates:
        cand_lower = cand.lower().strip()
        
        if "." not in cand_lower:
            continue
            
        # Add http prefix if not present so urlparse works
        if not cand_lower.startswith("http://") and not cand_lower.startswith("https://"):
            url = "http://" + cand_lower
        else:
            url = cand_lower
            
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc:
                if netloc.startswith("www."):
                    netloc = netloc[4:]
                # Verify that the parsed netloc ends with a valid TLD
                # This filters out regular words parsed as domains
                if any(netloc.endswith(tld) for tld in [".com", ".in", ".org", ".net", ".info", ".co", ".io", ".xyz"]):
                    # Ignore common words parsed as domains (e.g. today, evening)
                    if netloc not in ["today", "evening", "tomorrow", "yesterday", "morning", "night", "week", "month", "year"]:
                        domains.append(netloc)
        except Exception:
            pass
            
    return list(set(domains))
