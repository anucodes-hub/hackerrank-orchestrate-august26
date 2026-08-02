from schemas import MultimodalSignals
from utils import get_logger

logger = get_logger("VoiceAgent")

class VoiceAgent:
    """Gemini Audio agent for voice note transcription, emotion/stress detection, and speech urgency analysis."""
    def analyze(self, media_id: str, media_type: str, context_builder) -> MultimodalSignals:
        media_proc = context_builder.media_processor
        res = media_proc.process_media(media_type, media_id)
        
        transcript = res.get("extracted_text", "")
        source = res.get("source", "none")
        lower_transcript = transcript.lower()

        # Emotion & Stress detection
        stress = "neutral"
        if any(kw in lower_transcript for kw in ["panic", "emergency", "please help", "crying", "fast"]):
            stress = "high_stress"
        elif any(kw in lower_transcript for kw in ["urgent", "asap", "call me"]):
            stress = "urgent_tone"

        urgency = stress in ["high_stress", "urgent_tone"]
        confidence = 0.95 if source == "gemini_audio" else 0.75

        return MultimodalSignals(
            text_summary=transcript[:100],
            voice_transcript=transcript,
            doc_type="voice_note",
            emotion_stress=stress,
            urgency_detected=urgency,
            media_confidence=confidence,
            media_source=source,
            hallucination_warning=(source == "fallback_csv")
        )
