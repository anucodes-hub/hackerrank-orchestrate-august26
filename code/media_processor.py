import os
import json
import time
import pandas as pd
from PIL import Image
from utils import get_logger, retry_api
from observability import metrics_collector
from config import (
    GEMINI_API_KEY,
    MODEL_NAME,
    DEBUG,
    ENABLE_MEDIA_CACHE,
    FORCE_REFRESH_CACHE,
    CACHE_FILE_PATH,
    IMAGE_ANALYSIS_PROMPT,
    AUDIO_ANALYSIS_PROMPT,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    RETRY_BACKOFF
)

import google.generativeai as genai

logger = get_logger("MediaProcessor")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY environment variable is not set. MediaProcessor will use fallback extraction.")

class MediaProcessor:
    def __init__(self, data_loader):
        self.images_df = data_loader.get("images")
        self.voice_df = data_loader.get("voice_notes")
        self.project_root = data_loader.dataset_path
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Loads cached media processing results from disk."""
        if ENABLE_MEDIA_CACHE and os.path.exists(CACHE_FILE_PATH):
            try:
                with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    logger.info(f"Loaded {len(cache_data)} cached media entries from {CACHE_FILE_PATH}")
                    return cache_data
            except Exception as e:
                logger.warning(f"Error loading media cache file: {e}. Initializing empty cache.")
        return {}

    def _save_cache(self):
        """Saves media processing results to disk cache."""
        if not ENABLE_MEDIA_CACHE:
            return
        try:
            os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
            with open(CACHE_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            logger.debug("Saved updated media cache to disk.")
        except Exception as e:
            logger.warning(f"Error saving media cache: {e}")

    def process_media(self, media_type, media_id):
        """Extracts OCR text, receipts, notice board info, or speech transcripts for media items."""
        if pd.isna(media_id) or not media_id or pd.isna(media_type):
            return {"extracted_text": "", "media_details": {}, "source": "none"}

        extracted_text = ""
        details = {}
        source = "none"
        cache_key = f"{media_type}:{media_id}"

        # 1. Check disk cache first unless force refresh is true
        if ENABLE_MEDIA_CACHE and not FORCE_REFRESH_CACHE and cache_key in self.cache:
            metrics_collector.record_cache_hit()
            cached_item = self.cache[cache_key]
            if media_type == "image":
                metrics_collector.record_ocr()
            elif media_type == "voice":
                metrics_collector.record_voice_transcription()

            if DEBUG:
                logger.info(f"[CACHE HIT] Key '{cache_key}': {cached_item['extracted_text'][:100]}...")

            return {
                "extracted_text": cached_item["extracted_text"],
                "media_details": cached_item.get("media_details", {}),
                "source": "cache"
            }

        metrics_collector.record_cache_miss()

        # 2. Extract metadata & physical file path
        if media_type == "image" and self.images_df is not None and not self.images_df.empty:
            match = self.images_df[self.images_df["image_id"] == media_id]
            if not match.empty:
                details = match.iloc[0].to_dict()
                file_path = os.path.join(self.project_root, details.get("file_path", ""))
                
                # Metadata columns check
                csv_text = (
                    str(details.get("ocr_text", "")) or 
                    str(details.get("caption", "")) or 
                    str(details.get("description", ""))
                ).strip()

                # Execute Real Gemini Multimodal Analysis if API key and file exist
                if GEMINI_API_KEY and os.path.exists(file_path):
                    metrics_collector.record_ocr()
                    try:
                        extracted_text = self._analyze_image_llm(file_path)
                        source = "gemini_vision"
                        if not extracted_text:
                            logger.warning(f"Gemini Vision returned empty text for {file_path}. Using fallback CSV metadata.")
                            metrics_collector.record_fallback()
                            extracted_text = csv_text
                            source = "fallback_csv"
                    except Exception as e:
                        logger.warning(f"Gemini Vision failed for {file_path} ({e}). Using fallback CSV metadata.")
                        metrics_collector.record_fallback()
                        extracted_text = csv_text
                        source = "fallback_csv"
                else:
                    if not os.path.exists(file_path):
                        logger.error(f"Image file missing on disk: {file_path}")
                    metrics_collector.record_fallback()
                    extracted_text = csv_text
                    source = "fallback_csv"

        elif media_type == "voice" and self.voice_df is not None and not self.voice_df.empty:
            match = self.voice_df[self.voice_df["voice_note_id"] == media_id]
            if not match.empty:
                details = match.iloc[0].to_dict()
                file_path = os.path.join(self.project_root, details.get("file_path", ""))
                
                csv_text = (
                    str(details.get("transcript", "")) or 
                    str(details.get("audio_text", ""))
                ).strip()

                if GEMINI_API_KEY and os.path.exists(file_path):
                    metrics_collector.record_voice_transcription()
                    try:
                        extracted_text = self._analyze_audio_llm(file_path)
                        source = "gemini_audio"
                        if not extracted_text:
                            logger.warning(f"Gemini Audio returned empty text for {file_path}. Using fallback CSV metadata.")
                            metrics_collector.record_fallback()
                            extracted_text = csv_text
                            source = "fallback_csv"
                    except Exception as e:
                        logger.warning(f"Gemini Audio failed for {file_path} ({e}). Using fallback CSV metadata.")
                        metrics_collector.record_fallback()
                        extracted_text = csv_text
                        source = "fallback_csv"
                else:
                    if not os.path.exists(file_path):
                        logger.error(f"Voice note file missing on disk: {file_path}")
                    metrics_collector.record_fallback()
                    extracted_text = csv_text
                    source = "fallback_csv"
        else:
            source = "unknown"

        result_text = (extracted_text or "").strip()

        # Update disk cache
        self.cache[cache_key] = {
            "extracted_text": result_text,
            "media_details": details,
            "timestamp": time.time()
        }
        self._save_cache()

        return {
            "extracted_text": result_text,
            "media_details": details,
            "source": source
        }

    @retry_api(max_retries=MAX_RETRIES, delay=RETRY_DELAY_SECONDS, backoff=RETRY_BACKOFF)
    def _analyze_image_llm(self, image_path: str) -> str:
        """Call Gemini Vision model to extract details, posters, coupons, receipts, and screenshots."""
        start_time = time.time()
        logger.info(f"Gemini Request [IMAGE]: {image_path}")
        try:
            img = Image.open(image_path)
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content([IMAGE_ANALYSIS_PROMPT, img])
            latency = round(time.time() - start_time, 3)
            
            res_text = response.text.strip() if response and response.text else ""
            metrics_collector.record_api_call(success=True, latency=latency)
            
            logger.info(f"Gemini Response [IMAGE SUCCESS] ({latency}s): {res_text[:150]}...")
            return res_text
        except Exception as e:
            latency = round(time.time() - start_time, 3)
            metrics_collector.record_api_call(success=False, latency=latency)
            logger.error(f"Gemini Response [IMAGE ERROR] ({latency}s): {e}")
            raise e

    @retry_api(max_retries=MAX_RETRIES, delay=RETRY_DELAY_SECONDS, backoff=RETRY_BACKOFF)
    def _analyze_audio_llm(self, audio_path: str) -> str:
        """Call Gemini model to transcribe voice note and extract urgency/tone."""
        start_time = time.time()
        logger.info(f"Gemini Request [AUDIO]: {audio_path}")
        try:
            with open(audio_path, 'rb') as f:
                audio_bytes = f.read()

            model = genai.GenerativeModel(MODEL_NAME)
            
            response = model.generate_content(
                contents=[
                    AUDIO_ANALYSIS_PROMPT,
                    {
                        "mime_type": "audio/mp3",
                        "data": audio_bytes
                    }
                ]
            )
            latency = round(time.time() - start_time, 3)
            res_text = response.text.strip() if response and response.text else ""
            metrics_collector.record_api_call(success=True, latency=latency)
            
            logger.info(f"Gemini Response [AUDIO SUCCESS] ({latency}s): {res_text[:150]}...")
            return res_text
        except Exception as e:
            latency = round(time.time() - start_time, 3)
            metrics_collector.record_api_call(success=False, latency=latency)
            logger.error(f"Gemini Response [AUDIO ERROR] ({latency}s): {e}")
            raise e