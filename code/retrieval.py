import pandas as pd
from schemas import UnifiedContext, AgentVote, NotificationLevel
from utils import get_logger
from config import RETRIEVAL_TOP_K, RETRIEVAL_TERM_OVERLAP_RATIO

logger = get_logger("RetrievalEngine")

class RetrievalEngine:
    def __init__(self, data_loader):
        self.history = data_loader.get("message_history")
        self.events = data_loader.get("message_events")

    def find_evidence(self, current_msg: dict, user_id: str, top_k: int = RETRIEVAL_TOP_K) -> dict:
        """Retrieves structured evidence details including message IDs, similarity score, and match type."""
        user_hist = self.history[self.history["user_id"] == user_id]
        if user_hist.empty:
            return {
                "evidence_message_ids": "none",
                "similarity_score": 0.0,
                "match_type": "none",
                "summary": "No historical messages found for this user."
            }

        curr_text = str(current_msg.get("message_text", "") or "").lower().strip()
        evidence_ids = []
        best_similarity = 0.0
        match_type = "recent_fallback"

        curr_words = set(curr_text.split()) if curr_text else set()

        # 1. Exact text substring or high term overlap match
        for _, row in user_hist.iterrows():
            past_text = str(row.get("message_text", "") or "").lower().strip()
            if not past_text:
                continue

            if curr_text and (curr_text in past_text or past_text in curr_text):
                evidence_ids.append(str(row["message_id"]))
                best_similarity = max(best_similarity, 0.95)
                match_type = "exact_text_match"
                continue

            past_words = set(past_text.split())
            if curr_words and len(curr_words):
                overlap = len(curr_words.intersection(past_words)) / max(1, len(curr_words))
                if overlap >= RETRIEVAL_TERM_OVERLAP_RATIO:
                    evidence_ids.append(str(row["message_id"]))
                    best_similarity = max(best_similarity, round(overlap, 2))
                    match_type = "high_term_overlap"

        # 2. Historical User Interaction Events (opened / replied)
        if self.events is not None and not self.events.empty:
            user_events = self.events[self.events["user_id"] == user_id]
            active_events = user_events[(user_events["message_opened"] == 1) | (user_events["message_replied"] == 1)]
            if not active_events.empty:
                interacted_ids = active_events.tail(top_k)["message_id"].astype(str).tolist()
                evidence_ids.extend(interacted_ids)
                if match_type == "recent_fallback":
                    match_type = "user_interaction_event"
                    best_similarity = max(best_similarity, 0.75)

        # 3. Fallback to recent history
        if not evidence_ids:
            recent_msgs = user_hist.tail(top_k)
            evidence_ids = [str(m) for m in recent_msgs["message_id"].tolist()]
            best_similarity = 0.50
            match_type = "recent_fallback"

        # Deduplicate and validate
        evidence_ids = list(dict.fromkeys(evidence_ids))[:top_k]
        valid_evidence_ids = [eid for eid in evidence_ids if eid in user_hist["message_id"].astype(str).values]
        
        evidence_str = ";".join(valid_evidence_ids) if valid_evidence_ids else "none"

        return {
            "evidence_message_ids": evidence_str,
            "similarity_score": best_similarity,
            "match_type": match_type,
            "summary": f"Retrieved {len(valid_evidence_ids)} evidence items via {match_type} (similarity: {best_similarity})."
        }

    def evaluate_vote(self, context: UnifiedContext) -> AgentVote:
        """Evaluates historical evidence clusters and casts a Retrieval Agent Vote directly."""
        msg = context.message
        user_id = context.user_id
        res = self.find_evidence(msg, user_id)

        sim = res.get("similarity_score", 0.0)
        match_type = res.get("match_type", "none")
        evidence_ids = res.get("evidence_message_ids", "none")

        vote = NotificationLevel.DIGEST
        conf = 0.75
        explanation = f"Retrieved past evidence ({match_type}, similarity: {sim})."

        if match_type == "exact_text_match" and sim >= 0.90:
            vote = NotificationLevel.MUTE if context.user_stats.get("dismissal_rate", 0) > 0.5 else NotificationLevel.DIGEST
            conf = 0.90
        elif match_type == "user_interaction_event":
            vote = NotificationLevel.NORMAL_NOTIFY
            conf = 0.85

        return AgentVote(
            agent_name="RetrievalAgent",
            vote=vote,
            confidence=conf,
            evidence=explanation,
            signals={"similarity_score": sim, "match_type": match_type, "evidence_ids": evidence_ids}
        )