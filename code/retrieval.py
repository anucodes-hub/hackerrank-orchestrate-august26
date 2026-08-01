import pandas as pd
from utils import get_logger

logger = get_logger("RetrievalEngine")

class RetrievalEngine:
    def __init__(self, data_loader):
        self.history = data_loader.get("message_history")
        self.events = data_loader.get("message_events")

    def find_evidence(self, current_msg, user_id, top_k=2):
        """Retrieves top historical evidence IDs relevant to the current message."""
        user_hist = self.history[self.history["user_id"] == user_id]
        if user_hist.empty:
            return "none"

        curr_text = str(current_msg.get("message_text", "")).lower().strip()
        evidence_ids = []

        # Extract context terms to match against historical text
        curr_words = set(curr_text.split()) if curr_text else set()

        # 1. Look for highly similar messages (e.g. repeated promotional campaigns or forwards)
        for _, row in user_hist.iterrows():
            past_text = str(row.get("message_text", "")).lower().strip()
            if not past_text:
                continue

            # Check exact sub-string match or high term overlap
            if curr_text and (curr_text in past_text or past_text in curr_text):
                evidence_ids.append(str(row["message_id"]))
                continue

            past_words = set(past_text.split())
            if curr_words and len(curr_words.intersection(past_words)) / max(1, len(curr_words)) > 0.6:
                evidence_ids.append(str(row["message_id"]))

        # 2. Add recent messages where the user performed an interaction (opened or replied)
        if self.events is not None and not self.events.empty:
            user_events = self.events[self.events["user_id"] == user_id]
            # Since message_opened and message_replied are 1/0 columns, check for active events
            active_events = user_events[(user_events["message_opened"] == 1) | (user_events["message_replied"] == 1)]
            if not active_events.empty:
                interacted_ids = active_events.tail(top_k)["message_id"].astype(str).tolist()
                evidence_ids.extend(interacted_ids)

        # 3. Fallback to the most recent historical messages
        if not evidence_ids:
            recent_msgs = user_hist.tail(top_k)
            evidence_ids = [str(m) for m in recent_msgs["message_id"].tolist()]

        # Deduplicate and limit to top_k
        evidence_ids = list(dict.fromkeys(evidence_ids))[:top_k]
        
        # Ensure evidence IDs exist in history
        valid_evidence_ids = [eid for eid in evidence_ids if eid in user_hist["message_id"].astype(str).values]
        
        return ";".join(valid_evidence_ids) if valid_evidence_ids else "none"