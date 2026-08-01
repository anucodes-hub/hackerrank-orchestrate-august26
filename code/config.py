import os

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.5-flash"  # standard fast model for text/media processing
DEBUG_GEMINI = os.getenv("DEBUG_GEMINI", "false").lower() == "true"

# Scoring weights for prioritization
WEIGHTS = {
    "conversation_personal": 0.30,
    "has_recent_interactions": 0.20,
    "group_membership_active": 0.15,
    "sender_is_favorite": 0.20,
    "reply_rate_multiplier": 0.25,
    "dismissal_rate_penalty": -0.30,
    "high_daily_load_penalty": -0.15,
    "opt_out_penalty": -0.50,
}

# Decision thresholds
THRESHOLDS = {
    "notify": 0.70,
    "digest": 0.35,
}

# Business report limit before triggering risk review
MAX_BIZ_REPORTS = 5

# Default Quiet Hours: 22:00 to 07:00 (10 PM to 7 AM)
DEFAULT_QUIET_START = 22
DEFAULT_QUIET_END = 7
