from schemas import NotificationDecision, UnifiedContext
from utils import get_logger

logger = get_logger("ExplanationAgent")

class ExplanationAgent:
    """Synthesizes dynamic, evidence-backed, non-repetitive reasoning attributing agent contributions."""
    def explain(self, decision: NotificationDecision, context: UnifiedContext) -> str:
        # If safety override triggered, use safety evidence
        safety_vote = next((v for v in decision.agent_votes if v.agent_name == "SafetyScamAgent"), None)
        if safety_vote and safety_vote.signals.get("safety_override"):
            return safety_vote.evidence

        user_id = context.user_id
        msg_id = decision.message_id
        action = decision.action
        m_type = decision.message_type
        
        text_snippet = (context.raw_text or context.unified_text or "")[:35].replace("\n", " ").strip()
        snippet_ref = f" regarding '{text_snippet}...'" if text_snippet else ""

        reasons = []

        # Find key agent contributions
        pers_vote = next((v for v in decision.agent_votes if v.agent_name == "UserPersonalizationAgent"), None)
        biz_vote = next((v for v in decision.agent_votes if v.agent_name == "BusinessTrustAgent"), None)
        fatigue_vote = next((v for v in decision.agent_votes if v.agent_name == "NotificationFatigueAgent"), None)
        ret_vote = next((v for v in decision.agent_votes if v.agent_name == "RetrievalAgent"), None)

        user_stats = context.user_stats
        dismiss_pct = int(user_stats.get("dismissal_rate", 0) * 100)
        reply_pct = int(user_stats.get("reply_rate", 0) * 100)

        if action == "notify":
            if context.multimodal.urgency_detected:
                reasons.append(f"Time-sensitive operational update in {msg_id}{snippet_ref} flagged by Multimodal & Priority Agents.")
            elif context.conversation_type == "personal":
                reasons.append(f"Direct personal message ({msg_id}) from priority contact for user {user_id} (user reply rate {reply_pct}%).")
            elif biz_vote and biz_vote.signals.get("active_order"):
                reasons.append(f"Active order update ({msg_id}) confirmed by Business Trust Agent for user {user_id}.")
            else:
                reasons.append(f"High priority score synthesized across agent network for message {msg_id} (user {user_id}).")

        elif action == "mute":
            if fatigue_vote and fatigue_vote.signals.get("dnd_active"):
                reasons.append(f"Low-urgency message {msg_id}{snippet_ref} muted during user {user_id}'s quiet hours window.")
            elif fatigue_vote and fatigue_vote.signals.get("high_fatigue"):
                load = fatigue_vote.signals.get("daily_load", context.daily_load)
                reasons.append(f"Message {msg_id}{snippet_ref} muted by Fatigue Agent for user {user_id} (daily load: {load} notifications).")
            elif context.forwarded_count > 2:
                reasons.append(f"Forwarded chain ({context.forwarded_count}x) in {msg_id} suppressed based on user {user_id}'s dismissal history ({dismiss_pct}% dismissal rate).")
            elif biz_vote and biz_vote.signals.get("opt_out"):
                reasons.append(f"Promotional update in {msg_id} muted because user {user_id} explicitly opted out.")
            else:
                reasons.append(f"Low engagement priority for message {msg_id}{snippet_ref} (user {user_id} dismissal rate: {dismiss_pct}%).")

        else:  # digest
            if biz_vote and biz_vote.signals.get("verified_business"):
                reasons.append(f"Standard business update ({msg_id}) batched into daily digest by Business Trust Agent for user {user_id}.")
            elif context.group_context:
                grp_name = context.group_context.get("info", {}).get("group_name", "group")
                reasons.append(f"Group update ({msg_id}) from {grp_name} batched for user {user_id}'s periodic review.")
            else:
                reasons.append(f"Standard {m_type} message ({msg_id}){snippet_ref} batched into daily digest for user {user_id}.")

        # Append retrieval match details if present
        if ret_vote and ret_vote.signals.get("match_type") not in ["none", "recent_fallback"]:
            match_type = ret_vote.signals.get("match_type")
            sim = ret_vote.signals.get("similarity_score")
            reasons.append(f"Matches past evidence ({match_type}, sim: {sim}).")

        # Append contradiction resolution note if present
        if decision.contradictions_resolved:
            reasons.append(f"[{decision.contradictions_resolved[0]}]")

        return " ".join(reasons)
