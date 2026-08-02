import time
import statistics
from collections import Counter
from utils import get_logger

logger = get_logger("Observability")

class MetricsCollector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance

    def reset(self):
        self.start_time = time.time()
        self.total_messages = 0
        self.api_calls_attempted = 0
        self.api_calls_succeeded = 0
        self.api_calls_failed = 0
        self.fallback_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.ocr_count = 0
        self.voice_transcription_count = 0
        self.latencies = []
        self.confidences = []
        self.actions_breakdown = Counter()
        self.message_types_breakdown = Counter()
        self.safety_triggers = Counter()
        self.personalization_signals = Counter()

    def record_api_call(self, success: bool, latency: float):
        self.api_calls_attempted += 1
        if success:
            self.api_calls_succeeded += 1
        else:
            self.api_calls_failed += 1
        self.latencies.append(latency)

    def record_cache_hit(self):
        self.cache_hits += 1

    def record_cache_miss(self):
        self.cache_misses += 1

    def record_ocr(self):
        self.ocr_count += 1

    def record_voice_transcription(self):
        self.voice_transcription_count += 1

    def record_fallback(self):
        self.fallback_count += 1

    def record_decision(self, action: str, message_type: str, confidence: float, safety_trigger=None, signals=None):
        self.total_messages += 1
        self.actions_breakdown[action] += 1
        self.message_types_breakdown[message_type] += 1
        self.confidences.append(confidence)

        if safety_trigger:
            self.safety_triggers[safety_trigger] += 1

        if signals:
            for sig in signals:
                self.personalization_signals[sig] += 1

    def summary(self) -> dict:
        total_time = round(time.time() - self.start_time, 3)
        avg_latency = round(statistics.mean(self.latencies), 3) if self.latencies else 0.0
        avg_confidence = round(statistics.mean(self.confidences), 3) if self.confidences else 0.0

        return {
            "total_execution_time_sec": total_time,
            "total_messages_processed": self.total_messages,
            "gemini_api_calls": {
                "attempted": self.api_calls_attempted,
                "succeeded": self.api_calls_succeeded,
                "failed": self.api_calls_failed,
                "avg_latency_sec": avg_latency
            },
            "media_processing": {
                "ocr_count": self.ocr_count,
                "voice_transcription_count": self.voice_transcription_count,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses
            },
            "fallback_count": self.fallback_count,
            "average_confidence": avg_confidence,
            "routing_action_distribution": dict(self.actions_breakdown),
            "message_type_distribution": dict(self.message_types_breakdown),
            "top_safety_triggers": dict(self.safety_triggers.most_common(5)),
            "top_personalization_signals": dict(self.personalization_signals.most_common(5))
        }

    def print_report(self):
        s = self.summary()
        print("\n====================================================")
        print("               PIPELINE OBSERVABILITY REPORT        ")
        print("====================================================")
        print(f"Total Execution Time:        {s['total_execution_time_sec']}s")
        print(f"Total Messages Processed:    {s['total_messages_processed']}")
        print(f"Gemini API Calls Succeeded:  {s['gemini_api_calls']['succeeded']} / {s['gemini_api_calls']['attempted']}")
        print(f"Gemini API Calls Failed:     {s['gemini_api_calls']['failed']}")
        print(f"Average API Latency:         {s['gemini_api_calls']['avg_latency_sec']}s")
        print(f"Media Cache Hits / Misses:   {s['media_processing']['cache_hits']} / {s['media_processing']['cache_misses']}")
        print(f"OCR Images Processed:        {s['media_processing']['ocr_count']}")
        print(f"Voice Notes Transcribed:     {s['media_processing']['voice_transcription_count']}")
        print(f"Fallback Executions:         {s['fallback_count']}")
        print(f"Average Decision Confidence: {s['average_confidence']}")
        print("\nRouting Action Distribution:")
        for act, cnt in s['routing_action_distribution'].items():
            print(f"  - {act.upper():<8}: {cnt}")
        print("\nTop Safety Triggers:")
        for trig, cnt in s['top_safety_triggers'].items():
            print(f"  - {trig}: {cnt}")
        print("\nTop Personalization Signals:")
        for sig, cnt in s['top_personalization_signals'].items():
            print(f"  - {sig}: {cnt}")
        print("====================================================\n")

metrics_collector = MetricsCollector()
