import os
import sys
import unittest
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from loader import DataLoader
from context_builder import ContextBuilder
from retrieval import RetrievalEngine
from safety import SafetyEngine
from routing_agent import RoutingAgent
from schemas import UnifiedContext

class TestRefactoredMultiAgentSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dataset_path = os.path.join(os.path.dirname(CODE_DIR), "dataset")
        cls.loader = DataLoader(dataset_path=dataset_path)
        cls.loader.load_csv_files()
        cls.cb = ContextBuilder(cls.loader)
        cls.retrieval = RetrievalEngine(cls.loader)
        cls.safety = SafetyEngine()

    def test_01_unified_context_builder(self):
        """Test ContextBuilder directly returns a UnifiedContext Dataclass."""
        sample_row = self.loader.get("messages").iloc[0]
        ctx = self.cb.build_context(sample_row)
        self.assertIsInstance(ctx, UnifiedContext)
        self.assertEqual(ctx.message_id, sample_row["message_id"])

    def test_02_refactored_agent_routing_execution(self):
        """Test full routing execution with refactored service engines and split multimodal agents."""
        agent = RoutingAgent(self.retrieval, self.safety)
        sample_row = self.loader.get("messages").iloc[0]
        
        raw_context = {
            "message": sample_row.to_dict(),
            "context_builder_ref": self.cb
        }

        decision = agent.route(raw_context)

        self.assertIn("message_id", decision)
        self.assertIn(decision["action"], ["notify", "digest", "mute"])
        self.assertIsInstance(decision["reason"], str)
        self.assertGreater(len(decision["reason"]), 10)
        self.assertGreater(decision["confidence"], 0.40)

if __name__ == "__main__":
    unittest.main()
