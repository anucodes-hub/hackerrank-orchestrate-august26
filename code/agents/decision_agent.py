from typing import List
from schemas import (
    UnifiedContext,
    AgentVote,
    NotificationLevel,
    NotificationDecision,
    map_level_to_action
)
from utils import get_logger

logger = get_logger("DecisionAgent")

class DecisionAgent:
    """Performs Agent Confidence Voting, Contradiction Resolution, and Internal 6-Level Mapping."""
    def decide(self, context: UnifiedContext, votes: List[AgentVote]) -> NotificationDecision:
        contradictions = []

        # 1. Safety Override Enforcement (Safety overrides everything)
        safety_vote = next((v for v in votes if v.agent_name == "SafetyScamAgent"), None)
        if safety_vote and safety_vote.signals.get("safety_override"):
            internal_level = safety_vote.vote
            action = map_level_to_action(internal_level)
            m_type = "scam" if internal_level in (NotificationLevel.MUTE, NotificationLevel.SILENT_ARCHIVE) else "personal"
            return NotificationDecision(
                message_id=context.message_id,
                action=action,
                message_type=m_type,
                reason=safety_vote.evidence,
                confidence=safety_vote.confidence,
                evidence_message_ids="none",
                internal_level=internal_level,
                agent_votes=votes,
                contradictions_resolved=["Safety override enforced against generic priority."]
            )

        # 2. Contradiction Detection & Resolution
        pers_vote = next((v for v in votes if v.agent_name == "UserPersonalizationAgent"), None)
        prio_vote = next((v for v in votes if v.agent_name == "PriorityScoringAgent"), None)
        fatigue_vote = next((v for v in votes if v.agent_name == "NotificationFatigueAgent"), None)

        if prio_vote and fatigue_vote:
            if prio_vote.vote in (NotificationLevel.HIGH_NOTIFY, NotificationLevel.NORMAL_NOTIFY) and fatigue_vote.vote == NotificationLevel.MUTE:
                contradictions.append("Priority Agent requested notification, but Fatigue Agent flagged quiet hours/high load.")

        # 3. Agent Confidence Weighted Voting
        level_weights = {
            NotificationLevel.CRITICAL_NOTIFY: 0.0,
            NotificationLevel.HIGH_NOTIFY: 0.0,
            NotificationLevel.NORMAL_NOTIFY: 0.0,
            NotificationLevel.DIGEST: 0.0,
            NotificationLevel.MUTE: 0.0,
            NotificationLevel.SILENT_ARCHIVE: 0.0,
        }

        total_conf = 0.0
        for v in votes:
            level_weights[v.vote] += v.confidence
            total_conf += v.confidence

        winning_level = max(level_weights, key=level_weights.get)
        action = map_level_to_action(winning_level)

        # Message type determination
        sub_scores = prio_vote.signals.get("sub_scores", {}) if prio_vote else {}
        m_type = prio_vote.signals.get("message_type", "business_update") if prio_vote else "business_update"

        # Calculate final dynamic confidence based on agent agreement
        winning_score = level_weights[winning_level]
        agreement_ratio = winning_score / max(1.0, total_conf)
        final_conf = round(max(0.40, min(0.99, 0.70 + (agreement_ratio * 0.28))), 2)

        retrieval_vote = next((v for v in votes if v.agent_name == "RetrievalAgent"), None)
        evidence_ids = retrieval_vote.signals.get("evidence_ids", "none") if retrieval_vote else "none"

        return NotificationDecision(
            message_id=context.message_id,
            action=action,
            message_type=m_type,
            reason="",  # Will be populated by ExplanationAgent
            confidence=final_conf,
            evidence_message_ids=evidence_ids,
            internal_level=winning_level,
            agent_votes=votes,
            contradictions_resolved=contradictions
        )
