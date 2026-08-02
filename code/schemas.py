from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum

class NotificationLevel(Enum):
    CRITICAL_NOTIFY = "critical_notify"
    HIGH_NOTIFY = "high_notify"
    NORMAL_NOTIFY = "normal_notify"
    DIGEST = "digest"
    MUTE = "mute"
    SILENT_ARCHIVE = "silent_archive"

def map_level_to_action(level: NotificationLevel) -> str:
    if level in (NotificationLevel.CRITICAL_NOTIFY, NotificationLevel.HIGH_NOTIFY, NotificationLevel.NORMAL_NOTIFY):
        return "notify"
    elif level == NotificationLevel.DIGEST:
        return "digest"
    else:  # MUTE, SILENT_ARCHIVE
        return "mute"

@dataclass
class AgentVote:
    agent_name: str
    vote: NotificationLevel
    confidence: float
    evidence: str
    signals: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultimodalSignals:
    text_summary: str
    ocr_text: str = ""
    doc_type: str = "text"
    voice_transcript: str = ""
    emotion_stress: str = "neutral"
    urgency_detected: bool = False
    media_confidence: float = 1.0
    media_source: str = "none"
    hallucination_warning: bool = False

@dataclass
class BehavioralProfile:
    user_id: str
    favorite_contacts: Set[str] = field(default_factory=set)
    category_affinities: Dict[str, float] = field(default_factory=dict)
    mean_reply_latency_sec: float = 300.0
    dnd_window: str = ""
    notification_fatigue_level: float = 0.0
    cold_start: bool = False

@dataclass
class RetrievalEvidence:
    evidence_message_ids: str
    similarity_score: float
    match_type: str
    summary: str
    past_outcome: Optional[str] = None
    cluster_topic: Optional[str] = None

@dataclass
class SafetyReport:
    is_safe: bool
    threat_level: str  # "none", "low", "medium", "critical"
    threat_type: str   # "none", "prompt_injection", "homograph", "typosquatting", "phishing_domain", "scam_keyword"
    evidence: str
    safety_vote: NotificationLevel = NotificationLevel.NORMAL_NOTIFY

@dataclass
class UnifiedContext:
    message_id: str
    message: Dict[str, Any]
    user_id: str
    conversation_type: str
    raw_text: str
    unified_text: str
    multimodal: MultimodalSignals
    behavioral_profile: BehavioralProfile
    user_stats: Dict[str, Any]
    group_context: Optional[Dict[str, Any]] = None
    business_context: Optional[Dict[str, Any]] = None
    sender_profile: Optional[Dict[str, Any]] = None
    temporal: Dict[str, Any] = field(default_factory=dict)
    dnd_active: bool = False
    daily_load: int = 0
    forwarded_count: int = 0

@dataclass
class NotificationDecision:
    message_id: str
    action: str  # "notify", "digest", "mute"
    message_type: str  # "personal", "urgent", "payment", "business_update", "promotion", "greeting", "forward", "scam"
    reason: str
    confidence: float
    evidence_message_ids: str
    internal_level: NotificationLevel
    agent_votes: List[AgentVote] = field(default_factory=list)
    contradictions_resolved: List[str] = field(default_factory=list)
