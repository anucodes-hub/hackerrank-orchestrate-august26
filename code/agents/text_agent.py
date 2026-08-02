from utils import get_logger
from config import HIGH_PRIORITY_URGENT_KEYWORDS, HIGH_PRIORITY_PAYMENT_KEYWORDS

logger = get_logger("TextAgent")

class TextAgent:
    """Analyzes text intent, keywords, and text urgency."""
    def analyze(self, raw_text: str) -> dict:
        lower_text = raw_text.lower()
        has_urgent = any(kw in lower_text for kw in HIGH_PRIORITY_URGENT_KEYWORDS)
        has_payment = any(kw in lower_text for kw in HIGH_PRIORITY_PAYMENT_KEYWORDS)
        
        return {
            "summary": raw_text[:100],
            "urgency": has_urgent or has_payment,
            "has_payment_trigger": has_payment
        }
