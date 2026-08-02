from schemas import UnifiedContext, AgentVote, NotificationLevel
from utils import get_logger

logger = get_logger("BusinessTrustAgent")

class BusinessTrustAgent:
    """Evaluates business brand verification, order/booking history, report counts, and opt-out history."""
    def evaluate(self, context: UnifiedContext) -> AgentVote:
        biz_ctx = context.business_context
        if not biz_ctx:
            return AgentVote(
                agent_name="BusinessTrustAgent",
                vote=NotificationLevel.NORMAL_NOTIFY if context.conversation_type == "personal" else NotificationLevel.DIGEST,
                confidence=0.75,
                evidence="Non-business account or direct 1-on-1 chat.",
                signals={"is_business": False}
            )

        biz_info = biz_ctx.get("info") or {}
        biz_hist = biz_ctx.get("user_history") or {}
        brand = biz_info.get("brand_name", "business account")
        is_verified = biz_info.get("is_verified", True)
        reports = biz_info.get("reports_count", 0)
        has_opted_out = biz_hist.get("has_opted_out", False)
        orders = biz_hist.get("recent_orders_count", 0) + biz_hist.get("recent_payments_count", 0)

        if has_opted_out:
            return AgentVote(
                agent_name="BusinessTrustAgent",
                vote=NotificationLevel.MUTE,
                confidence=0.95,
                evidence=f"User opted out from promotional updates from {brand}.",
                signals={"opt_out": True}
            )

        if reports >= 5 or not is_verified:
            return AgentVote(
                agent_name="BusinessTrustAgent",
                vote=NotificationLevel.MUTE,
                confidence=0.90,
                evidence=f"Unverified or highly reported business {brand} ({reports} reports).",
                signals={"unverified_reported": True}
            )

        if orders > 0:
            return AgentVote(
                agent_name="BusinessTrustAgent",
                vote=NotificationLevel.HIGH_NOTIFY,
                confidence=0.88,
                evidence=f"Active purchase/booking order history exists for {brand}.",
                signals={"active_order": True}
            )

        return AgentVote(
            agent_name="BusinessTrustAgent",
            vote=NotificationLevel.DIGEST,
            confidence=0.80,
            evidence=f"Standard update from verified business {brand}.",
            signals={"verified_business": is_verified}
        )
