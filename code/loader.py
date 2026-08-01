import os
import pandas as pd
from utils import get_logger

logger = get_logger("DataLoader")

DATASET_PATH = "dataset"
REQUIRED_FILES = {
    "messages": "messages.csv",
    "users": "users.csv",
    "groups": "groups.csv",
    "group_members": "group_members.csv",
    "business_accounts": "business_accounts.csv",
    "user_business_history": "user_business_history.csv",
    "message_history": "message_history.csv",
    "message_events": "message_events.csv",
    "images": "images.csv",
    "voice_notes": "voice_notes.csv",
    "daily_notification_summary": "daily_notification_summary.csv",
}

class DataLoader:
    def __init__(self, dataset_path=DATASET_PATH):
        self.dataset_path = dataset_path
        self.data = {}
        self.history_index = {}
        self.biz_history_index = {}
        self.user_stats = {}

    def load_csv_files(self):
        logger.info("Loading dataset files...")
        for name, filename in REQUIRED_FILES.items():
            file_path = os.path.join(self.dataset_path, filename)
            if not os.path.exists(file_path):
                logger.error(f"Missing required file: {file_path}")
                raise FileNotFoundError(f"Missing required file: {file_path}")
            self.data[name] = pd.read_csv(file_path)
            logger.debug(f"Loaded {filename}: {len(self.data[name])} rows")

        self._build_indexes()
        self._calculate_user_statistics()
        logger.info("All datasets, hash indexes, and stats loaded successfully!")
        return self.data

    def _build_indexes(self):
        """Pre-indexes large historical files for O(1) lookup performance."""
        hist_df = self.data["message_history"]
        for u_id, group in hist_df.groupby("user_id"):
            self.history_index[u_id] = group.to_dict(orient="records")

        biz_hist_df = self.data["user_business_history"]
        for _, row in biz_hist_df.iterrows():
            key = (row["user_id"], row["business_id"])
            self.biz_history_index[key] = row.to_dict()

    def _calculate_user_statistics(self):
        """Pre-compute personalized behavior statistics for users from profiles."""
        users_df = self.data["users"]
        for _, row in users_df.iterrows():
            u_id = row["user_id"]
            opened = row.get("messages_opened_30d", 0)
            replied = row.get("messages_replied_30d", 0)
            dismissed = row.get("notifications_dismissed_30d", 0)
            reported = row.get("messages_reported_30d", 0)
            
            # Safe rates (avoid divide by zero)
            total_handled = opened + dismissed
            reply_rate = replied / max(1.0, opened)
            dismissal_rate = dismissed / max(1.0, total_handled)
            report_rate = reported / max(1.0, total_handled)
            
            self.user_stats[u_id] = {
                "reply_rate": round(reply_rate, 4),
                "dismissal_rate": round(dismissal_rate, 4),
                "report_rate": round(report_rate, 4),
                "dnd_window": row.get("do_not_disturb_window", None)
            }

    def get(self, name):
        return self.data.get(name)

    def get_user_history(self, user_id):
        return self.history_index.get(user_id, [])

    def get_user_biz_history(self, user_id, biz_id):
        return self.biz_history_index.get((user_id, biz_id), {})

    def get_user_stats(self, user_id):
        """Get pre-calculated statistics for a user."""
        return self.user_stats.get(user_id, {
            "reply_rate": 0.0,
            "dismissal_rate": 0.0,
            "report_rate": 0.0,
            "dnd_window": None
        })