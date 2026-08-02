import os
from schemas import UnifiedContext, AgentVote, NotificationLevel
from utils import get_logger, extract_domains
from config import (
    MAX_BIZ_REPORTS,
    SCAM_KEYWORDS,
    TRUSTED_DOMAINS,
    PROMPT_INJECTION_PATTERNS,
    SENSITIVE_ACTION_KEYWORDS
)

logger = get_logger("SafetyEngine")

class SafetyEngine:
    """Security engine checking phishing domains, prompt injection, typosquatting, and scam keywords."""
    def __init__(self):
        self.scam_keywords = SCAM_KEYWORDS
        self.trusted_domains = TRUSTED_DOMAINS
        self.prompt_injection_patterns = PROMPT_INJECTION_PATTERNS
        self.sensitive_keywords = SENSITIVE_ACTION_KEYWORDS

    def evaluate_vote(self, context: UnifiedContext) -> AgentVote:
        """Evaluates safety guardrails and casts a Safety Agent Vote directly with override capability."""
        unified_text = context.unified_text.lower()
        user_prof = context.user_stats
        grp_ctx = context.group_context
        biz_ctx = context.business_context

        # 1. Prompt Injection / Instruction Override Attack Guardrail
        for pattern in self.prompt_injection_patterns:
            if pattern in unified_text:
                return AgentVote(
                    agent_name="SafetyScamAgent",
                    vote=NotificationLevel.SILENT_ARCHIVE,
                    confidence=0.99,
                    evidence=f"Security attack blocked: prompt injection pattern '{pattern}' detected.",
                    signals={"safety_override": True, "threat_type": "prompt_injection"}
                )

        # 2. Phishing Domain Extraction & Verification
        extracted_domains = extract_domains(context.unified_text)
        for domain in extracted_domains:
            is_trusted = any(td in domain for td in self.trusted_domains)
            if not is_trusted:
                return AgentVote(
                    agent_name="SafetyScamAgent",
                    vote=NotificationLevel.SILENT_ARCHIVE,
                    confidence=0.98,
                    evidence=f"Phishing guardrail triggered: suspicious unverified domain '{domain}' found in link.",
                    signals={"safety_override": True, "threat_type": "phishing_domain", "domain": domain}
                )

        # 3. Unverified Business requesting sensitive credentials
        biz_info = (biz_ctx.get("info") if biz_ctx else {}) or {}
        if biz_info:
            reports = biz_info.get("reports_count", 0)
            is_verified = biz_info.get("is_verified", True)
            if reports >= MAX_BIZ_REPORTS or not is_verified:
                if any(kw in unified_text for kw in self.sensitive_keywords):
                    return AgentVote(
                        agent_name="SafetyScamAgent",
                        vote=NotificationLevel.SILENT_ARCHIVE,
                        confidence=0.98,
                        evidence="Unverified business requesting sensitive authentication/payment credentials.",
                        signals={"safety_override": True, "threat_type": "fake_otp"}
                    )

        # 4. Static Scam Keyword Guardrails
        for kw in self.scam_keywords:
            if kw in unified_text:
                return AgentVote(
                    agent_name="SafetyScamAgent",
                    vote=NotificationLevel.SILENT_ARCHIVE,
                    confidence=0.98,
                    evidence=f"Security guardrail triggered: text matches scam phrase ('{kw}').",
                    signals={"safety_override": True, "threat_type": "scam_keyword", "keyword": kw}
                )

        # 5. Muted Group Rule with Direct Mention Override
        if grp_ctx and grp_ctx.get("membership", {}).get("is_muted"):
            username = str(user_prof.get("username", "") or "").lower()
            if username and f"@{username}" in unified_text:
                logger.info(f"Direct mention override for muted group member: @{username}")
            else:
                grp_name = grp_ctx.get("info", {}).get("group_name", "group chat")
                return AgentVote(
                    agent_name="SafetyScamAgent",
                    vote=NotificationLevel.MUTE,
                    confidence=0.95,
                    evidence=f"{grp_name} is muted by user preferences and contains no direct mention.",
                    signals={"safety_override": True, "threat_type": "muted_group"}
                )

        return AgentVote(
            agent_name="SafetyScamAgent",
            vote=NotificationLevel.NORMAL_NOTIFY,
            confidence=0.95,
            evidence="Safety check passed: no security threats detected.",
            signals={"safety_override": False, "threat_type": "none"}
        )