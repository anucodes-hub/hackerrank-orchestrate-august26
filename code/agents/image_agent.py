from schemas import MultimodalSignals
from utils import get_logger

logger = get_logger("ImageAgent")

class ImageAgent:
    """Gemini Vision agent for complete understanding of receipts, bills, posters, QR codes, and medical documents."""
    def analyze(self, media_id: str, media_type: str, context_builder) -> MultimodalSignals:
        media_proc = context_builder.media_processor
        res = media_proc.process_media(media_type, media_id)
        
        extracted_text = res.get("extracted_text", "")
        source = res.get("source", "none")
        lower_text = extracted_text.lower()

        # Document classification & Intent extraction
        doc_type = "image"
        if "receipt" in lower_text or "total" in lower_text or "paid" in lower_text:
            doc_type = "receipt"
        elif "invoice" in lower_text or "bill" in lower_text or "due date" in lower_text:
            doc_type = "bill"
        elif "prescription" in lower_text or "doctor" in lower_text or "clinic" in lower_text:
            doc_type = "medical_document"
        elif "circular" in lower_text or "school" in lower_text or "class" in lower_text:
            doc_type = "school_notice"
        elif "qr code" in lower_text or "scan to pay" in lower_text:
            doc_type = "payment_qr"

        urgency = any(kw in lower_text for kw in ["urgent", "immediately", "due today", "expiry"])
        confidence = 0.95 if source == "gemini_vision" else 0.75

        return MultimodalSignals(
            text_summary=extracted_text[:100],
            ocr_text=extracted_text,
            doc_type=doc_type,
            urgency_detected=urgency,
            media_confidence=confidence,
            media_source=source,
            hallucination_warning=(source == "fallback_csv")
        )
