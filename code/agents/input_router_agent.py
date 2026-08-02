from schemas import MultimodalSignals
from agents.text_agent import TextAgent
from agents.image_agent import ImageAgent
from agents.voice_agent import VoiceAgent
from utils import get_logger

logger = get_logger("InputRouterAgent")

class InputRouterAgent:
    """Routes incoming message payloads to specialized Text, Image, and Voice agents."""
    def __init__(self, text_agent: TextAgent = None, image_agent: ImageAgent = None, voice_agent: VoiceAgent = None):
        self.text_agent = text_agent or TextAgent()
        self.image_agent = image_agent or ImageAgent()
        self.voice_agent = voice_agent or VoiceAgent()

    def process(self, message_row: dict, context_builder) -> MultimodalSignals:
        media_type = str(message_row.get("media_type") or "").lower().strip()
        media_id = message_row.get("media_id")
        raw_text = str(message_row.get("message_text") or "").strip()

        # 1. Process Text Component
        text_signals = self.text_agent.analyze(raw_text)

        # 2. Process Image / Document Component if present
        image_signals = None
        if media_type in ["image", "photo", "document"]:
            image_signals = self.image_agent.analyze(media_id, media_type, context_builder)

        # 3. Process Voice / Audio Component if present
        voice_signals = None
        if media_type in ["audio", "voice", "voice_note"]:
            voice_signals = self.voice_agent.analyze(media_id, media_type, context_builder)

        # Combine Multimodal Signals
        ocr_text = image_signals.ocr_text if image_signals else ""
        voice_transcript = voice_signals.voice_transcript if voice_signals else ""
        doc_type = image_signals.doc_type if image_signals else ("voice_note" if voice_signals else "text")
        emotion_stress = voice_signals.emotion_stress if voice_signals else "neutral"
        urgency = text_signals.get("urgency", False) or (image_signals.urgency_detected if image_signals else False) or (voice_signals.urgency_detected if voice_signals else False)
        media_conf = min(
            image_signals.media_confidence if image_signals else 1.0,
            voice_signals.media_confidence if voice_signals else 1.0
        )
        media_source = image_signals.media_source if image_signals else (voice_signals.media_source if voice_signals else "none")

        return MultimodalSignals(
            text_summary=text_signals.get("summary", raw_text),
            ocr_text=ocr_text,
            doc_type=doc_type,
            voice_transcript=voice_transcript,
            emotion_stress=emotion_stress,
            urgency_detected=urgency,
            media_confidence=media_conf,
            media_source=media_source,
            hallucination_warning=False
        )
