import os
import json
from typing import Dict, Any, Set
from utils import get_logger

logger = get_logger("LearningStore")

class LearningStore:
    """Manages state updates from user feedback and historical interaction tracking."""
    def __init__(self, store_path: str = "dataset/learning_state.json"):
        self.store_path = store_path
        self.ignored_notify_counts: Dict[str, int] = {}
        self.favorite_senders: Dict[str, Set[str]] = {}
        self.scam_reports: Set[str] = set()
        self.category_opens: Dict[str, Dict[str, int]] = {}
        self._load()

    def record_ignored_notification(self, user_id: str, sender_id: str):
        key = f"{user_id}:{sender_id}"
        self.ignored_notify_counts[key] = self.ignored_notify_counts.get(key, 0) + 1

    def is_frequently_ignored(self, user_id: str, sender_id: str, threshold: int = 5) -> bool:
        key = f"{user_id}:{sender_id}"
        return self.ignored_notify_counts.get(key, 0) >= threshold

    def add_scam_report(self, term: str):
        if term:
            self.scam_reports.add(term.lower())

    def record_category_open(self, user_id: str, category: str):
        if user_id not in self.category_opens:
            self.category_opens[user_id] = {}
        self.category_opens[user_id][category] = self.category_opens[user_id].get(category, 0) + 1

    def get_category_affinity(self, user_id: str, category: str) -> float:
        user_map = self.category_opens.get(user_id, {})
        total = sum(user_map.values())
        if total == 0:
            return 0.50
        return round(user_map.get(category, 0) / total, 2)

    def _load(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.ignored_notify_counts = data.get("ignored_counts", {})
                    self.scam_reports = set(data.get("scam_reports", []))
                    self.category_opens = data.get("category_opens", {})
            except Exception as e:
                logger.warning(f"Failed to load LearningStore: {e}")

    def save(self):
        try:
            data = {
                "ignored_counts": self.ignored_notify_counts,
                "scam_reports": list(self.scam_reports),
                "category_opens": self.category_opens
            }
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save LearningStore: {e}")
