from schemas import UnifiedContext, AgentVote, NotificationLevel
from config import (
    SUB_SCORE_WEIGHTS,
    THRESHOLDS,
    FATIGUE_DAILY_LIMIT,
    HIGH_PRIORITY_PAYMENT_KEYWORDS,
    HIGH_PRIORITY_URGENT_KEYWORDS,
    MAX_BIZ_REPORTS
)
from utils import get_logger

logger = get_logger("ScoringEngine")

class ScoringEngine:
    def __init__(self):
        self.weights = SUB_SCORE_WEIGHTS

    def compute_scores(self, context: dict, retrieval_info: dict) -> dict:
        """Computes 12 independent explainable sub-scores and applies combinatorial condition matrix routing."""
        msg = context["message"]
        unified_text = context["unified_text"].lower()
        user_stats = context.get("user_stats") or {}
        user_profile = context.get("user_profile") or {}
        biz_ctx = context.get("business_context") or {}
        grp_ctx = context.get("group_context") or {}
        daily_load = context.get("daily_load", 0)
        fwd_count = context.get("forwarded_count", 0)
        temporal = context.get("temporal") or {}

        signals_used = []
        evidence_factors = []

        # 1. Urgency Score (0.0 to 1.0)
        urgency_score = 0.30
        if any(kw in unified_text for kw in HIGH_PRIORITY_URGENT_KEYWORDS):
            urgency_score += 0.50
            signals_used.append("urgent_keyword_detected")
            evidence_factors.append("urgent keyword in text/transcript")
        if any(kw in unified_text for kw in HIGH_PRIORITY_PAYMENT_KEYWORDS):
            urgency_score += 0.40
            signals_used.append("payment_otp_keyword_detected")
            evidence_factors.append("payment/OTP keyword detected")
        urgency_score = min(1.0, urgency_score)

        # 2. Trust Score (0.0 to 1.0)
        trust_score = 0.50
        if msg.get("conversation_type") == "personal":
            trust_score += 0.30
            signals_used.append("personal_chat_trusted")
            evidence_factors.append("1-on-1 personal conversation")
        elif biz_ctx:
            biz_info = biz_ctx.get("info") or {}
            if biz_info.get("is_verified"):
                trust_score += 0.25
                signals_used.append("verified_business")
                evidence_factors.append("verified business sender")
            reports = biz_info.get("reports_count", 0)
            if reports > 0:
                trust_score -= min(0.40, reports * 0.08)
                signals_used.append("business_reported_penalty")

        # 3. Risk Score (0.0 to 1.0)
        risk_score = 0.10
        if biz_ctx:
            biz_info = biz_ctx.get("info") or {}
            if biz_info.get("reports_count", 0) >= MAX_BIZ_REPORTS:
                risk_score += 0.60
                signals_used.append("high_business_report_count")
                evidence_factors.append(f"business reported {biz_info.get('reports_count')} times")
            if not biz_info.get("is_verified", True):
                risk_score += 0.25
                signals_used.append("unverified_business_account")
        if fwd_count > 3:
            risk_score += min(0.30, fwd_count * 0.05)
            signals_used.append("frequently_forwarded_chain")
            evidence_factors.append(f"forwarded {fwd_count} times")
        risk_score = min(1.0, risk_score)

        # 4. Relationship Score (0.0 to 1.0)
        reply_rate = user_stats.get("reply_rate", 0.0)
        dismiss_rate = user_stats.get("dismissal_rate", 0.0)
        relationship_score = 0.40
        if msg.get("conversation_type") == "personal":
            relationship_score += 0.35
        if reply_rate > 0.4:
            relationship_score += 0.20
            signals_used.append("favorite_high_reply_contact")
            evidence_factors.append(f"user reply rate {int(reply_rate * 100)}%")
        relationship_score = min(1.0, relationship_score)

        # 5. Business Trust Score (-0.5 to +0.5)
        biz_score = 0.0
        biz_hist = biz_ctx.get("user_history") or {} if biz_ctx else {}
        if biz_hist:
            if biz_hist.get("has_opted_out"):
                biz_score -= 0.45
                signals_used.append("user_opted_out_from_business")
                evidence_factors.append("user opted out from marketing")
            if biz_hist.get("recent_orders_count", 0) > 0 or biz_hist.get("recent_payments_count", 0) > 0:
                biz_score += 0.35
                signals_used.append("recent_orders_or_bookings_exist")
                evidence_factors.append("active order/booking history")

        # 6. Conversation Continuity Score (0.0 to 1.0)
        continuity_score = 0.40
        recent_hist = context.get("recent_history", [])
        if len(recent_hist) > 3:
            continuity_score += 0.30
            signals_used.append("active_conversation_continuity")
            evidence_factors.append("recent thread messages exist")

        # 7. Personalization Score (0.0 to 1.0)
        personalization_score = 0.50 + (reply_rate * 0.25) - (dismiss_rate * 0.30)
        personalization_score = max(0.0, min(1.0, personalization_score))

        # 8. Historical Engagement Score (0.0 to 1.0)
        opened_count = user_profile.get("messages_opened_30d", 0)
        dismissed_count = user_profile.get("notifications_dismissed_30d", 0)
        total_handled = max(1, opened_count + dismissed_count)
        historical_engagement_score = round(opened_count / total_handled, 2)

        # 9. Notification Fatigue Score (Penalty: 0.0 to 0.5)
        fatigue_score = 0.0
        if daily_load > FATIGUE_DAILY_LIMIT:
            fatigue_score += 0.25
            signals_used.append("notification_fatigue_penalty")
            evidence_factors.append(f"daily load {daily_load} notifications")
        if temporal.get("dnd_active"):
            fatigue_score += 0.20
            signals_used.append("quiet_hours_active")
            evidence_factors.append("during preferred quiet hours")

        # 10. Time Sensitivity Score (0.0 to 1.0)
        time_sensitivity_score = urgency_score
        if any(term in unified_text for term in ["today", "tonight", "mins", "hours", "now"]):
            time_sensitivity_score = min(1.0, time_sensitivity_score + 0.30)
            evidence_factors.append("time-bound deadline today")

        # 11. Media Confidence & 12. Retrieval Similarity Score
        media_confidence_score = 0.90 if context.get("media_text") else 1.0
        retrieval_similarity_score = retrieval_info.get("similarity_score", 0.50)

        # Build Sub-Scores Dict
        sub_scores = {
            "urgency_score": round(urgency_score, 2),
            "trust_score": round(trust_score, 2),
            "risk_score": round(risk_score, 2),
            "relationship_score": round(relationship_score, 2),
            "business_trust_score": round(biz_score, 2),
            "conversation_continuity_score": round(continuity_score, 2),
            "personalization_score": round(personalization_score, 2),
            "historical_engagement_score": round(historical_engagement_score, 2),
            "notification_fatigue_score": round(fatigue_score, 2),
            "time_sensitivity_score": round(time_sensitivity_score, 2),
            "media_confidence_score": round(media_confidence_score, 2),
            "retrieval_similarity_score": round(retrieval_similarity_score, 2)
        }

        # Combinatorial Matrix Condition Evaluator
        action = "digest"
        m_type = "business_update"

        if urgency_score >= 0.7 and risk_score >= 0.5:
            action = "mute"
            m_type = "scam"
        elif urgency_score >= 0.7 and trust_score >= 0.6:
            action = "notify"
            m_type = "payment" if "payment_otp_keyword_detected" in signals_used else "urgent"
        elif biz_score > 0.2 and trust_score >= 0.6:
            action = "notify"
            m_type = "business_update"
        elif biz_score < -0.3 or (biz_ctx and dismiss_rate > 0.6):
            action = "mute"
            m_type = "promotion"
        elif fwd_count > 2 or (fwd_count > 0 and fatigue_score > 0.3):
            action = "mute"
            m_type = "forward" if fwd_count > 2 else "greeting"
        elif msg.get("conversation_type") == "personal" and relationship_score >= 0.7:
            action = "notify" if urgency_score > 0.5 else "digest"
            m_type = "personal"
        elif urgency_score < 0.4 and fatigue_score >= 0.35:
            action = "mute"
            m_type = "greeting" if "good morning" in unified_text else "promotion"
        else:
            weighted_total = (
                (urgency_score * 0.25) +
                (trust_score * 0.20) +
                (relationship_score * 0.15) +
                (biz_score * 0.15) -
                (risk_score * 0.20) -
                (fatigue_score * 0.15)
            )
            if weighted_total >= THRESHOLDS["notify"]:
                action = "notify"
                m_type = "urgent" if urgency_score > 0.6 else "business_update"
            elif weighted_total <= THRESHOLDS["digest"]:
                action = "mute"
                m_type = "promotion" if msg.get("conversation_type") == "business" else "greeting"
            else:
                action = "digest"
                m_type = "event" if "event" in unified_text or "form" in unified_text else "business_update"

        return {
            "action": action,
            "message_type": m_type,
            "sub_scores": sub_scores,
            "signals_used": signals_used,
            "evidence_factors": evidence_factors
        }

    def evaluate_vote(self, context: UnifiedContext, retrieval_vote: AgentVote) -> AgentVote:
        """Evaluates 12 sub-scores directly returning a Priority Agent Vote."""
        ret_info = {
            "similarity_score": retrieval_vote.signals.get("similarity_score", 0.5),
            "match_type": retrieval_vote.signals.get("match_type", "none"),
            "evidence_message_ids": retrieval_vote.signals.get("evidence_ids", "none")
        }
        
        ctx_dict = {
            "message": context.message,
            "unified_text": context.unified_text,
            "user_stats": context.user_stats,
            "user_profile": context.message.get("user_profile"),
            "business_context": context.business_context,
            "group_context": context.group_context,
            "sender_profile": context.sender_profile,
            "daily_load": context.daily_load,
            "forwarded_count": context.forwarded_count,
            "is_cold_start": context.behavioral_profile.cold_start,
            "temporal": context.temporal,
            "media_text": context.multimodal.ocr_text or context.multimodal.voice_transcript
        }

        res = self.compute_scores(ctx_dict, ret_info)
        action = res["action"]
        sub = res["sub_scores"]

        if action == "notify":
            vote = NotificationLevel.HIGH_NOTIFY if sub["urgency_score"] > 0.6 else NotificationLevel.NORMAL_NOTIFY
        elif action == "mute":
            vote = NotificationLevel.MUTE
        else:
            vote = NotificationLevel.DIGEST

        return AgentVote(
            agent_name="PriorityScoringAgent",
            vote=vote,
            confidence=0.85,
            evidence=f"Priority scoring: urgency {sub['urgency_score']}, trust {sub['trust_score']}, risk {sub['risk_score']}.",
            signals=res
        )
