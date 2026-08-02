from safety import SafetyEngine

class RiskDetector:
    """Wrapper class linking risk detection to SafetyEngine for backwards compatibility."""
    def __init__(self):
        self.engine = SafetyEngine()

    def detect_risk(self, context: dict) -> dict:
        return self.engine.evaluate(context)
