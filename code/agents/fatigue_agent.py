from schemas import UnifiedContext, AgentVote, NotificationLevel
from utils import get_logger
from config import FATIGUE_DAILY_LIMIT

logger = get_logger("NotificationFatigueAgent")

class NotificationFatigueAgent:
    """Evaluates daily notification volume, quiet window active state, and notification fatigue level."""
    def evaluate(self, context: UnifiedContext) -> AgentVote:
        daily_load = context.daily_load
        dnd_active = context.dnd_active
        user_id = context.user_id

        if dnd_active:
            return AgentVote(
                agent_name="NotificationFatigueAgent",
                vote=NotificationLevel.MUTE,
                confidence=0.90,
                evidence=f"Low-urgency message received during user {user_id}'s quiet hours.",
                signals={"dnd_active": True}
            )

        if daily_load > FATIGUE_DAILY_LIMIT:
            return AgentVote(
                agent_name="NotificationFatigueAgent",
                vote=NotificationLevel.MUTE,
                confidence=0.85,
                evidence=f"High notification fatigue for user {user_id} (daily volume: {daily_load} notifications).",
                signals={"high_fatigue": True, "daily_load": daily_load}
            )

        return AgentVote(
            agent_name="NotificationFatigueAgent",
            vote=NotificationLevel.DIGEST,
            confidence=0.75,
            evidence=f"Normal daily notification load ({daily_load} notifications).",
            signals={"daily_load": daily_load}
        )
