from schemas import UnifiedContext, AgentVote, NotificationLevel
from utils import get_logger

logger = get_logger("UserPersonalizationAgent")

class UserPersonalizationAgent:
    """Evaluates rich behavioral profiles, category affinities, reply preferences, and cold-start state."""
    def __init__(self, learning_store=None):
        self.learning_store = learning_store

    def evaluate(self, context: UnifiedContext) -> AgentVote:
        user_id = context.user_id
        user_stats = context.user_stats
        reply_rate = user_stats.get("reply_rate", 0.0)
        dismiss_rate = user_stats.get("dismissal_rate", 0.0)
        is_cold_start = context.behavioral_profile.cold_start

        # Cold Start Handling (Requirement 11)
        if is_cold_start:
            return AgentVote(
                agent_name="UserPersonalizationAgent",
                vote=NotificationLevel.NORMAL_NOTIFY if context.conversation_type == "personal" else NotificationLevel.DIGEST,
                confidence=0.65,
                evidence=f"Cold-start profile for user {user_id}: fallback to conversation metadata.",
                signals={"cold_start": True}
            )

        # Behavioral Affinity Evaluation
        vote = NotificationLevel.DIGEST
        conf = 0.80
        evidence = f"User {user_id} behavioral stats: {int(reply_rate * 100)}% reply rate, {int(dismiss_rate * 100)}% dismissal rate."

        if context.conversation_type == "personal" and reply_rate > 0.40:
            vote = NotificationLevel.HIGH_NOTIFY
            conf = 0.90
            evidence = f"High priority personal contact for user {user_id} (reply rate {int(reply_rate * 100)}%)."
        elif dismiss_rate > 0.60 or context.forwarded_count > 2:
            vote = NotificationLevel.MUTE
            conf = 0.85
            evidence = f"User {user_id} frequently dismisses low engagement/forwarded messages ({int(dismiss_rate * 100)}% dismissal rate)."

        return AgentVote(
            agent_name="UserPersonalizationAgent",
            vote=vote,
            confidence=conf,
            evidence=evidence,
            signals={"reply_rate": reply_rate, "dismissal_rate": dismiss_rate}
        )
