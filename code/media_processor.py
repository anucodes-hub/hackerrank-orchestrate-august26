import os
import pandas as pd
from PIL import Image
from utils import get_logger, retry_api
import google.generativeai as genai

logger = get_logger("MediaProcessor")

# Set up Gemini client configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY env variable is not set. MediaProcessor will fall back to CSV-only metadata.")

class MediaProcessor:
    def __init__(self, data_loader):
        self.images_df = data_loader.get("images")
        self.voice_df = data_loader.get("voice_notes")
        self.project_root = data_loader.dataset_path

    def process_media(self, media_type, media_id):
        """Extracts OCR text, transcripts, or metadata for images and voice notes."""
        if pd.isna(media_id) or not media_id or pd.isna(media_type):
            return {"extracted_text": "", "media_details": {}}

        extracted_text = ""
        details = {}

        if media_type == "image" and self.images_df is not None and not self.images_df.empty:
            match = self.images_df[self.images_df["image_id"] == media_id]
            if not match.empty:
                details = match.iloc[0].to_dict()
                file_path = os.path.join(self.project_root, details.get("file_path", ""))
                
                # Check for CSV metadata fallback
                csv_text = (
                    str(details.get("ocr_text", "")) or 
                    str(details.get("caption", "")) or 
                    str(details.get("description", ""))
                ).strip()

                # Attempt LLM Multimodal processing
                if GEMINI_API_KEY and os.path.exists(file_path):
                    from config import DEBUG_GEMINI
                    if DEBUG_GEMINI:
                        print(f"[DEBUG GEMINI] Processing Image: {file_path}")
                        llm_ocr = self._analyze_image_llm(file_path)
                        print(f"[DEBUG GEMINI] Image Result: {llm_ocr[:200] if llm_ocr else None}")
                        extracted_text = llm_ocr if llm_ocr else csv_text
                    else:
                        try:
                            llm_ocr = self._analyze_image_llm(file_path)
                            if llm_ocr:
                                extracted_text = llm_ocr
                            else:
                                extracted_text = csv_text
                        except Exception as e:
                            logger.warning(f"Error performing LLM image analysis: {e}. Falling back to CSV metadata.")
                            extracted_text = csv_text
                else:
                    extracted_text = csv_text

        elif media_type == "voice" and self.voice_df is not None and not self.voice_df.empty:
            match = self.voice_df[self.voice_df["voice_note_id"] == media_id]
            if not match.empty:
                details = match.iloc[0].to_dict()
                file_path = os.path.join(self.project_root, details.get("file_path", ""))
                
                # Check for CSV metadata fallback
                csv_text = (
                    str(details.get("transcript", "")) or 
                    str(details.get("audio_text", ""))
                ).strip()

                if GEMINI_API_KEY and os.path.exists(file_path):
                    from config import DEBUG_GEMINI
                    if DEBUG_GEMINI:
                        print(f"[DEBUG GEMINI] Processing Audio: {file_path}")
                        llm_transcript = self._analyze_audio_llm(file_path)
                        print(f"[DEBUG GEMINI] Audio Result: {llm_transcript[:200] if llm_transcript else None}")
                        extracted_text = llm_transcript if llm_transcript else csv_text
                    else:
                        try:
                            llm_transcript = self._analyze_audio_llm(file_path)
                            if llm_transcript:
                                extracted_text = llm_transcript
                            else:
                                extracted_text = csv_text
                        except Exception as e:
                            logger.warning(f"Error performing LLM audio analysis: {e}. Falling back to CSV metadata.")
                            extracted_text = csv_text
                else:
                    extracted_text = csv_text

        return {
            "extracted_text": extracted_text.strip(),
            "media_details": details
        }

    @retry_api(max_retries=3, delay=1.0)
    def _analyze_image_llm(self, image_path):
        """Use Gemini model to extract text, notice boards, coupons, or receipts from image."""
        try:
            logger.info(f"Analyzing image using Gemini: {image_path}")
            img = Image.open(image_path)
            from config import MODEL_NAME
            model = genai.GenerativeModel(MODEL_NAME)
            
            prompt = (
                "Extract all text, notices, dates, receipts, prices, event names, and coupon codes "
                "from this image. Be extremely accurate. If it is a QR code or payment poster, describe "
                "the text and details clearly. Output only the extracted details."
            )
            response = model.generate_content([prompt, img])
            return response.text
        except Exception as e:
            logger.error(f"Error performing LLM image analysis: {e}")
            return None

    @retry_api(max_retries=3, delay=1.0)
    def _analyze_audio_llm(self, audio_path):
        """Use Gemini model to transcribe and identify urgency/tone from audio files."""
        try:
            logger.info(f"Analyzing voice note using Gemini: {audio_path}")
            
            # Read the audio file bytes and upload using API
            with open(audio_path, 'rb') as f:
                audio_bytes = f.read()

            from config import MODEL_NAME
            model = genai.GenerativeModel(MODEL_NAME)
            
            prompt = (
                "Transcribe this voice note completely. If there is urgency, payment requests, "
                "or panic in the tone/background, summarize the tone or urgency clearly at the end. "
                "Transcribe the actual speech precisely."
            )
            
            # Format audio upload payload
            response = model.generate_content(
                contents=[
                    prompt,
                    {
                        "mime_type": "audio/mp3",
                        "data": audio_bytes
                    }
                ]
            )
            return response.text
        except Exception as e:
            logger.error(f"Error performing LLM audio analysis: {e}")
            return None