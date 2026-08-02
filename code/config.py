import os
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

# --- Gemini API & Model Settings ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")

# --- Debug & Mode Flags ---
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
DEBUG_GEMINI = os.getenv("DEBUG_GEMINI", "false").lower() == "true" or DEBUG

# --- Media Caching Settings ---
ENABLE_MEDIA_CACHE = os.getenv("ENABLE_MEDIA_CACHE", "true").lower() == "true"
FORCE_REFRESH_CACHE = os.getenv("FORCE_REFRESH_CACHE", "false").lower() == "true"
CACHE_FILE_PATH = os.path.join("dataset", "media_cache.json")

# --- API Resilience Settings ---
API_TIMEOUT_SECONDS = int(os.getenv("API_TIMEOUT_SECONDS", "15"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS = float(os.getenv("RETRY_DELAY_SECONDS", "1.0"))
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "2.0"))

# --- 12 Independent Sub-Score Weights ---
SUB_SCORE_WEIGHTS = {
    "urgency": float(os.getenv("WEIGHT_URGENCY", "0.20")),
    "trust": float(os.getenv("WEIGHT_TRUST", "0.15")),
    "risk": float(os.getenv("WEIGHT_RISK", "-0.25")),
    "relationship": float(os.getenv("WEIGHT_RELATIONSHIP", "0.15")),
    "business_trust": float(os.getenv("WEIGHT_BIZ_TRUST", "0.15")),
    "conversation_continuity": float(os.getenv("WEIGHT_CONTINUITY", "0.10")),
    "personalization": float(os.getenv("WEIGHT_PERSONALIZATION", "0.15")),
    "historical_engagement": float(os.getenv("WEIGHT_HIST_ENGAGEMENT", "0.10")),
    "notification_fatigue": float(os.getenv("WEIGHT_FATIGUE", "-0.15")),
    "time_sensitivity": float(os.getenv("WEIGHT_TIME_SENSITIVITY", "0.15")),
    "media_confidence": float(os.getenv("WEIGHT_MEDIA_CONF", "0.05")),
    "retrieval_similarity": float(os.getenv("WEIGHT_RETRIEVAL_SIM", "0.05")),
}

# --- Action Thresholds ---
THRESHOLDS = {
    "notify": float(os.getenv("THRESHOLD_NOTIFY", "0.68")),
    "digest": float(os.getenv("THRESHOLD_DIGEST", "0.38")),
}

# --- Business Safety & Report Limits ---
MAX_BIZ_REPORTS = int(os.getenv("MAX_BIZ_REPORTS", "5"))

# --- Quiet Hours / DND Defaults ---
DEFAULT_QUIET_START = int(os.getenv("DEFAULT_QUIET_START_HOUR", "22"))
DEFAULT_QUIET_END = int(os.getenv("DEFAULT_QUIET_END_HOUR", "7"))

# --- Notification Fatigue Settings ---
FATIGUE_DAILY_LIMIT = int(os.getenv("FATIGUE_DAILY_LIMIT", "40"))

# --- Retrieval Parameters ---
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "2"))
RETRIEVAL_TERM_OVERLAP_RATIO = float(os.getenv("RETRIEVAL_TERM_OVERLAP_RATIO", "0.6"))

# --- Guardrail Checklist Lists ---
SCAM_KEYWORDS = [
    "lottery", "claim prize", "wire money", "kyc update urgent",
    "bank account suspended", "crypto bonus", "account-login.in",
    "chase-secure-alert.com", "verify now", "profile will be blocked",
    "confirm password and otp", "wallet verification failed"
]

TRUSTED_DOMAINS = [
    "amazon.com", "amazon.in", "fedex.com", "razorpay.com",
    "pvr", "chase.com", "shopee", "google.com", "whatsapp.com"
]

PROMPT_INJECTION_PATTERNS = [
    "routing override", "ignore sender risk", "always mark this",
    "system note for", "assistant instruction:", "ignore all previous",
    "override routing rules", "override routing", "ignore previous"
]

SENSITIVE_ACTION_KEYWORDS = [
    "payment", "verify", "link", "login", "bank", "otp", "code", "password"
]

HIGH_PRIORITY_PAYMENT_KEYWORDS = [
    "otp", "verification code", "credited", "debited", "paid", "refund", "invoice"
]

HIGH_PRIORITY_URGENT_KEYWORDS = [
    "urgent", "emergency", "asap", "call me now", "heads-up", "leaving", "early", "immediately"
]

ALLOWED_ACTIONS = {"notify", "digest", "mute"}
ALLOWED_MESSAGE_TYPES = {
    "personal", "urgent", "event", "payment", "business_update",
    "promotion", "greeting", "forward", "spam", "scam", "unknown"
}

IMAGE_ANALYSIS_PROMPT = (
    "Extract all text, notices, dates, receipts, prices, event names, and coupon codes "
    "from this image. Be extremely accurate. If it is a QR code, receipt, screenshot, or payment poster, describe "
    "the text and details clearly. Output only the extracted details."
)

AUDIO_ANALYSIS_PROMPT = (
    "Transcribe this voice note completely. If there is urgency, payment requests, "
    "or panic in the tone/background, summarize the tone or urgency clearly at the end. "
    "Transcribe the actual speech precisely."
)
