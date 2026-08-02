import pandas as pd
from datetime import datetime
from media_processor import MediaProcessor
from utils import get_logger
from config import DEFAULT_QUIET_START, DEFAULT_QUIET_END
from schemas import UnifiedContext, BehavioralProfile, MultimodalSignals

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

    def build_context(self, message_row, multimodal_signals: MultimodalSignals = None) -> UnifiedContext:
        """Builds a comprehensive unified semantic context directly returning a strongly-typed UnifiedContext Dataclass."""
        msg_dict = message_row if isinstance(message_row, dict) else message_row.to_dict()
        user_id = msg_dict["user_id"]
        conv_type = msg_dict["conversation_type"]
        group_id = msg_dict.get("group_id")
        biz_id = msg_dict.get("business_id")
        sender_user_id = msg_dict.get("sender_user_id")
        msg_time_str = msg_dict["created_at"]
        fwd_count = int(msg_dict.get("forwarded_count", 0) or 0)

        # 1. Media Extraction if multimodal_signals is not pre-supplied
        if multimodal_signals is None:
            media_data = self.media_processor.process_media(
                msg_dict.get("media_type"),
                msg_dict.get("media_id")
            )
            msg_text = str(msg_dict.get("message_text", "") or "").strip()
            media_text = str(media_data.get("extracted_text", "") or "").strip()
            unified_text = f"{msg_text} {media_text}".strip()
            
            multimodal_signals = MultimodalSignals(
                text_summary=msg_text[:100],
                ocr_text=media_text if msg_dict.get("media_type") in ["image", "photo"] else "",
                voice_transcript=media_text if msg_dict.get("media_type") in ["audio", "voice", "voice_note"] else "",
                doc_type=msg_dict.get("media_type") or "text",
                media_confidence=0.95 if media_data.get("source") != "fallback_csv" else 0.75,
                media_source=media_data.get("source", "none")
            )
        else:
            msg_text = str(msg_dict.get("message_text", "") or "").strip()
            media_text = multimodal_signals.ocr_text or multimodal_signals.voice_transcript
            unified_text = f"{msg_text} {media_text}".strip()

        # 2. User Profile & Calculated Stats
        user_profile = self._get_user(user_id)
        user_stats = self.loader.get_user_stats(user_id)
        is_cold_start = self._check_cold_start(user_profile, user_stats)

        # 3. Temporal Context & Active Quiet Hours Calculation
        temporal_info = self._get_temporal_info(msg_time_str, user_stats.get("dnd_window"))

        # 4. Group & Business Context (Fully Detailed)
        group_ctx = self._get_group(group_id, user_id) if conv_type == "group" else None
        biz_ctx = self._get_business(biz_id, user_id) if conv_type == "business" else None
        sender_profile = self._get_user(sender_user_id) if sender_user_id and not pd.isna(sender_user_id) else {}

        # 5. History & Interaction Continuity Signals
        recent_history = self.loader.get_user_history(user_id)[-10:]
        daily_load = self._get_daily_load(user_id)

        # 6. Construct Behavioral Profile
        profile = BehavioralProfile(
            user_id=user_id,
            dnd_window=user_stats.get("dnd_window", ""),
            notification_fatigue_level=0.5 if daily_load > 40 else 0.1,
            cold_start=is_cold_start
        )

        return UnifiedContext(
            message_id=msg_dict["message_id"],
            message=msg_dict,
            user_id=user_id,
            conversation_type=conv_type,
            raw_text=msg_text,
            unified_text=unified_text,
            multimodal=multimodal_signals,
            behavioral_profile=profile,
            user_stats=user_stats,
            group_context=group_ctx,
            business_context=biz_ctx,
            sender_profile=sender_profile,
            temporal=temporal_info,
            dnd_active=temporal_info["dnd_active"],
            daily_load=daily_load,
            forwarded_count=fwd_count
        )

    def _get_user(self, user_id):
        if pd.isna(user_id) or not user_id:
            return {}
        df = self.users[self.users["user_id"] == user_id]
        return df.iloc[0].to_dict() if not df.empty else {}

    def _get_group(self, group_id, user_id):
        if pd.isna(group_id) or not group_id:
            return None
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
        if pd.isna(biz_id) or not biz_id:
            return None
        biz = self.business[self.business["business_id"] == biz_id]
        hist = self.loader.get_user_biz_history(user_id, biz_id)
        return {
            "info": biz.iloc[0].to_dict() if not biz.empty else {},
            "user_history": hist
        }

    def _check_cold_start(self, user_profile: dict, user_stats: dict) -> bool:
        opened = user_profile.get("messages_opened_30d", 0)
        dismissed = user_profile.get("notifications_dismissed_30d", 0)
        return (opened + dismissed) < 5

    def _get_temporal_info(self, created_at_str: str, dnd_window: str) -> dict:
        try:
            msg_dt = pd.to_datetime(created_at_str)
            msg_time = msg_dt.time()
            hour = msg_dt.hour
            day_of_week = msg_dt.day_name()
            
            dnd_active = False
            if dnd_window and not pd.isna(dnd_window):
                start_str, end_str = str(dnd_window).split("-")
                start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
                end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
                
                if start_time <= end_time:
                    dnd_active = start_time <= msg_time <= end_time
                else:  # Crosses midnight (e.g. 22:00-07:00)
                    dnd_active = msg_time >= start_time or msg_time <= end_time
            else:
                dnd_active = hour >= DEFAULT_QUIET_START or hour < DEFAULT_QUIET_END

            return {
                "created_at": created_at_str,
                "hour": hour,
                "day_of_week": day_of_week,
                "dnd_active": dnd_active,
                "dnd_window": dnd_window
            }
        except Exception as e:
            logger.warning(f"Error parsing temporal timestamp '{created_at_str}': {e}")
            return {
                "created_at": created_at_str,
                "hour": 12,
                "day_of_week": "Unknown",
                "dnd_active": False,
                "dnd_window": dnd_window
            }

    def _get_daily_load(self, user_id):
        if self.daily_summary is None or self.daily_summary.empty:
            return 0
            
        df = self.daily_summary[self.daily_summary["user_id"] == user_id]
        if df.empty:
            return 0

        for col in ["notifications_sent", "notification_count", "notifications_count", "count", "total_notifications"]:
            if col in df.columns:
                return int(df[col].sum())

        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            return int(df[numeric_cols[0]].sum())

        return len(df)