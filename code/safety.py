import os
import google.generativeai as genai
from utils import get_logger, extract_domains, retry_api
from config import MAX_BIZ_REPORTS

logger = get_logger("SafetyEngine")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

class SafetyEngine:
    def __init__(self):
        # Local keyword checklist for fallback/sanity checks
        self.scam_keywords = ["lottery", "claim prize", "wire money", "kyc update urgent", "bank account suspended", "crypto bonus", "account-login.in", "chase-secure-alert.com"]
        # Explicit domains we know are trusted
        self.trusted_domains = ["amazon.com", "amazon.in", "fedex.com", "razorpay.com", "pvr", "chase.com", "shopee"]

    def evaluate(self, context):
        msg = context["message"]
        msg_text = str(msg.get("message_text", "") or "")
        media_text = str(context.get("media_text", "") or "")
        full_text = f"{msg_text} {media_text}".strip()

        user_prof = context.get("user_profile") or {}
        grp_ctx = context.get("group_context") or {}
        biz_ctx = context.get("business_context") or {}

        # 1. Phishing Domain Extraction & Verification
        extracted_domains = extract_domains(full_text)
        for domain in extracted_domains:
            # Check if domain looks suspicious and is not in trusted_domains
            is_trusted = any(td in domain for td in self.trusted_domains)
            if not is_trusted:
                logger.info(f"Unsafe/suspicious domain detected: {domain}")
                return {
                    "action": "mute",
                    "message_type": "scam",
                    "reason": f"Suspicious or unverified domain found in message link: {domain}",
                    "confidence": 0.98
                }

        # 2. Instruction Override / Jailbreak Guardrail Check
        lower_full_text = full_text.lower()
        if "routing override" in lower_full_text or "ignore sender risk" in lower_full_text or "always mark this" in lower_full_text or "system note for" in lower_full_text or "assistant instruction:" in lower_full_text:
            logger.info("Jailbreak / system instruction override attempt blocked.")
            return {
                "action": "mute",
                "message_type": "scam",
                "reason": "Security pattern blocked: message text contains instructions intended for system override.",
                "confidence": 0.99
            }

        # 3. Unverified Senders / Phishing Risk Check
        biz_info = biz_ctx.get("info") or {}
        if biz_info:
            reports = biz_info.get("reports_count", 0)
            is_verified = biz_info.get("is_verified", True)
            if reports > MAX_BIZ_REPORTS or not is_verified:
                if any(kw in lower_full_text for kw in ["payment", "verify", "link", "login", "bank", "otp", "code"]):
                    return {
                        "action": "mute",
                        "message_type": "scam",
                        "reason": "Unverified or highly reported business account requesting sensitive authentication/payment actions.",
                        "confidence": 0.98
                    }

        # 4. Local Scam Keyword Check (Fallback)
        for kw in self.scam_keywords:
            if kw in lower_full_text:
                return {
                    "action": "mute",
                    "message_type": "scam",
                    "reason": f"Suspicious security pattern detected matching static guardrails ('{kw}').",
                    "confidence": 0.98
                }

        # 5. Muted Group Logic with Direct Mention Override
        if grp_ctx and grp_ctx.get("membership", {}).get("is_muted"):
            username = str(user_prof.get("username", "") or "").lower()
            # If user is directly mentioned, override mute rule
            if username and f"@{username}" in lower_full_text:
                return None  # Pass to priority router
            
            return {
                "action": "mute",
                "message_type": "personal" if msg.get("conversation_type") == "group" else "unknown",
                "reason": "Group is muted by user preferences and contains no direct mention.",
                "confidence": 0.95
            }

        return None