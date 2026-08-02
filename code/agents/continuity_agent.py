from schemas import UnifiedContext, AgentVote, NotificationLevel
from utils import get_logger

logger = get_logger("ConversationContinuityAgent")

class ConversationContinuityAgent:
    """Evaluates active thread continuity, recent user reply windows, and ongoing conversations."""
    def evaluate(self, context: UnifiedContext) -> AgentVote:
        recent_hist = context.message.get("recent_history", [])
        msg_id = context.message_id
        
        is_active_thread = len(recent_hist) > 2
        vote = NotificationLevel.HIGH_NOTIFY if is_active_thread and context.conversation_type == "personal" else NotificationLevel.DIGEST
        conf = 0.85 if is_active_thread else 0.70
        explanation = f"Active conversation thread detected for message {msg_id}." if is_active_thread else f"Single or standalone message {msg_id}."

        return AgentVote(
            agent_name="ConversationContinuityAgent",
            vote=vote,
            confidence=conf,
            evidence=explanation,
            signals={"active_thread": is_active_thread}
        )
