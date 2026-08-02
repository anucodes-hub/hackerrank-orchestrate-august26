# Configuration Guide - Message Notification Router

This document provides a comprehensive guide to all environment variables, configuration parameters, scoring weights, thresholds, retry parameters, and safety settings in `code/config.py` and `.env`.

---

## Environment Variables (`.env`)

Create a `.env` file in the project root based on `.env.example`:

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | `""` | Google Gemini API Key for multimodal OCR, voice transcription, and LLM reasoning. |
| `MODEL_NAME` | `gemini-2.0-flash` | Target Gemini model identifier (`gemini-2.0-flash`, `gemini-1.5-flash`, `gemini-3.6-flash`). |
| `DEBUG` | `false` | Enables verbose step-by-step debug logging across the pipeline. |
| `DEBUG_GEMINI` | `false` | Logs full Gemini API prompts, requests, and responses. |
| `ENABLE_MEDIA_CACHE` | `true` | Enables disk-backed media caching (`dataset/media_cache.json`) for OCR/transcriptions. |
| `FORCE_REFRESH_CACHE`| `false` | Bypasses disk cache and forces fresh Gemini API calls. |
| `API_TIMEOUT_SECONDS`| `15` | Timeout limit for external API calls in seconds. |
| `MAX_RETRIES` | `3` | Maximum retry attempts for transient API errors. |
| `RETRY_DELAY_SECONDS`| `1.0` | Initial delay between API retry attempts. |
| `RETRY_BACKOFF` | `2.0` | Exponential backoff multiplier for API retries. |

---

## Prioritization Scoring Weights (`WEIGHTS`)

Configured in `code/config.py`:

```python
WEIGHTS = {
    "conversation_personal": 0.30,      # Boost for personal 1-on-1 conversations
    "has_recent_interactions": 0.20,    # Boost for active order/booking business relationship
    "group_membership_active": 0.15,    # Boost for active group participation
    "sender_is_favorite": 0.20,         # Boost for high user reply rate senders
    "reply_rate_multiplier": 0.25,      # Multiplier for user reply history
    "dismissal_rate_penalty": -0.30,   # Penalty for high historical dismissal rate
    "high_daily_load_penalty": -0.15,  # Notification fatigue penalty
    "opt_out_penalty": -0.50,          # Penalty for business accounts user opted out from
}
```

---

## Action Decision Thresholds (`THRESHOLDS`)

```python
THRESHOLDS = {
    "notify": 0.70,   # Final score >= 0.70 triggers immediate notification
    "digest": 0.35,   # Final score <= 0.35 triggers mute; between 0.35 and 0.70 triggers digest
}
```

---

## Business Safety & Quiet Hours Settings

- `MAX_BIZ_REPORTS`: `5` (Maximum user report count allowed before unverified business account triggers scam guardrails).
- `DEFAULT_QUIET_START`: `22` (10 PM - Start of default quiet hours).
- `DEFAULT_QUIET_END`: `7` (7 AM - End of default quiet hours).
- `FATIGUE_DAILY_LIMIT`: `40` (Daily notification load count before fatigue dampening applies).

---

## Safety Checklists & Prompts

- `SCAM_KEYWORDS`: List of static scam/phishing terms.
- `TRUSTED_DOMAINS`: Trusted domain whitelist (`amazon.com`, `razorpay.com`, etc.).
- `PROMPT_INJECTION_PATTERNS`: Substrings for detecting instruction override attacks.
- `IMAGE_ANALYSIS_PROMPT`: Custom vision prompt for posters, receipts, coupons, and notices.
- `AUDIO_ANALYSIS_PROMPT`: Custom audio prompt for speech transcription and tone/urgency extraction.
