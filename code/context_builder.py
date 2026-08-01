import pandas as pd
from datetime import datetime
from media_processor import MediaProcessor
from utils import get_logger

logger = get_logger("ContextBuilder")

class ContextBuilder:
    def __init__(self, data_loader):
        self.loader = data_loader
        self.messages = data_loader.get("messages")
        self.users = data_loader.get("users")
        self.groups = data_loader.get("groups")
        self.group_members = data_loader.get("group_members")
        self.business = data_loader.get("business_accounts")
        self.daily_summary = data_loader.get("daily_notification_summary")
        self.media_processor = MediaProcessor(data_loader)

    def build_context(self, message_row):
        user_id = message_row["user_id"]
        conv_type = message_row["conversation_type"]
        group_id = message_row.get("group_id")
        biz_id = message_row.get("business_id")
        msg_time_str = message_row["created_at"]

        # Process media content (OCR text or voice transcripts)
        media_data = self.media_processor.process_media(
            message_row.get("media_type"),
            message_row.get("media_id")
        )

        user_profile = self._get_user(user_id)
        user_stats = self.loader.get_user_stats(user_id)

        # Compute DND / Quiet Hours active flag
        dnd_active = self._check_dnd_active(user_stats.get("dnd_window"), msg_time_str)

        return {
            "message": message_row.to_dict(),
            "media_text": media_data["extracted_text"],
            "media_details": media_data["media_details"],
            "user_profile": user_profile,
            "user_stats": user_stats,
            "dnd_active": dnd_active,
            "conversation_type": conv_type,
            "group_context": self._get_group(group_id, user_id) if conv_type == "group" else None,
            "business_context": self._get_business(biz_id, user_id) if conv_type == "business" else None,
            "recent_history": self.loader.get_user_history(user_id)[-10:],
            "daily_load": self._get_daily_load(user_id)
        }

    def _get_user(self, user_id):
        df = self.users[self.users["user_id"] == user_id]
        return df.iloc[0].to_dict() if not df.empty else {}

    def _get_group(self, group_id, user_id):
        grp = self.groups[self.groups["group_id"] == group_id]
        mem = self.group_members[
            (self.group_members["group_id"] == group_id) & 
            (self.group_members["user_id"] == user_id)
        ]
        return {
            "info": grp.iloc[0].to_dict() if not grp.empty else {},
            "membership": mem.iloc[0].to_dict() if not mem.empty else {}
        }

    def _get_business(self, biz_id, user_id):
        biz = self.business[self.business["business_id"] == biz_id]
        hist = self.loader.get_user_biz_history(user_id, biz_id)
        return {
            "info": biz.iloc[0].to_dict() if not biz.empty else {},
            "user_history": hist
        }

    def _check_dnd_active(self, dnd_window, created_at_str):
        """Check if message creation time falls within user DND window."""
        if not dnd_window or pd.isna(dnd_window):
            return False
        try:
            # Parse created_at e.g. '2026-07-30 22:19' or standard ISO
            msg_dt = pd.to_datetime(created_at_str)
            msg_time = msg_dt.time()
            
            start_str, end_str = dnd_window.split("-")
            start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
            end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
            
            if start_time <= end_time:
                return start_time <= msg_time <= end_time
            else:  # Crosses midnight (e.g. 22:00-07:00)
                return msg_time >= start_time or msg_time <= end_time
        except Exception as e:
            logger.warning(f"Error parsing DND window '{dnd_window}': {e}")
            return False

    def _get_daily_load(self, user_id):
        if self.daily_summary is None or self.daily_summary.empty:
            return 0
            
        df = self.daily_summary[self.daily_summary["user_id"] == user_id]
        if df.empty:
            return 0

        # Try common column names safely
        for col in ["notifications_sent", "notification_count", "notifications_count", "count", "total_notifications"]:
            if col in df.columns:
                return int(df[col].sum())

        # Fallback: sum any numeric column that isn't user_id or date
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            return int(df[numeric_cols[0]].sum())

        return len(df)  # Final fallback: count rows for this user