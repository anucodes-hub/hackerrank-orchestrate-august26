import os
import sys
import argparse
import pandas as pd

# Reconfigure standard output to UTF-8 to prevent Windows CP1252 UnicodeEncodeErrors
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from loader import DataLoader
from context_builder import ContextBuilder
from retrieval import RetrievalEngine
from safety import SafetyEngine
from routing_agent import RoutingAgent
from observability import metrics_collector
from utils import get_logger
from config import DEBUG

logger = get_logger("MainPipeline")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")
OUTPUT_PATH = os.path.join(DATASET_DIR, "output.csv")

def parse_args():
    parser = argparse.ArgumentParser(description="WhatsApp Message Notification Router Pipeline")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
    return parser.parse_args()

def main():
    args = parse_args()
    is_debug = args.debug or DEBUG

    print("=== Starting Multi-Agent WhatsApp Notification Router Pipeline ===")

    try:
        os.makedirs(DATASET_DIR, exist_ok=True)

        # 1. Initialize Data Loader
        loader = DataLoader(dataset_path=DATASET_DIR)
        data = loader.load_csv_files()
        messages_df = data["messages"]

        if messages_df is None or messages_df.empty:
            logger.error("dataset/messages.csv is empty or missing!")
            sys.exit(1)

        # 2. Initialize Core Engines & Multi-Agent Network
        context_builder = ContextBuilder(loader)
        retrieval_engine = RetrievalEngine(loader)
        safety_engine = SafetyEngine()
        routing_agent = RoutingAgent(retrieval_engine, safety_engine)

        results = []
        print(f"\nProcessing {len(messages_df)} incoming messages through Multi-Agent System...")
        
        for idx, row in messages_df.iterrows():
            try:
                # Build context dict with reference
                raw_context = {
                    "message": row.to_dict(),
                    "context_builder_ref": context_builder
                }

                # Get routing decision from Multi-Agent System
                decision = routing_agent.route(raw_context)

                if is_debug:
                    print(f"[DEBUG] Message ID: {row['message_id']} -> Action: {decision['action']}, Type: {decision['message_type']}, Conf: {decision['confidence']}")

                # Format output record
                results.append({
                    "message_id": row["message_id"],
                    "action": decision["action"],
                    "message_type": decision["message_type"],
                    "reason": decision["reason"],
                    "confidence": round(float(decision["confidence"]), 2),
                    "evidence_message_ids": decision["evidence_message_ids"]
                })
            except Exception as msg_err:
                logger.error(f"Error processing row {idx} ({row.get('message_id')}): {msg_err}")
                # Fallback record to ensure zero crashes
                results.append({
                    "message_id": row.get("message_id", f"msg_error_{idx}"),
                    "action": "digest",
                    "message_type": "unknown",
                    "reason": f"System error handling message: {str(msg_err)[:100]}",
                    "confidence": 0.50,
                    "evidence_message_ids": "none"
                })

        # 3. Create DataFrame and Export output.csv
        output_df = pd.DataFrame(results)

        required_columns = ["message_id", "action", "message_type", "reason", "confidence", "evidence_message_ids"]
        for col in required_columns:
            if col not in output_df.columns:
                output_df[col] = "none"

        output_df = output_df[required_columns]
        output_df.to_csv(OUTPUT_PATH, index=False)
        print(f"\n[SUCCESS] Generated output.csv with {len(output_df)} predictions!")
        print(f"Saved to: {OUTPUT_PATH}")

        print("\nFirst 5 predictions preview:")
        print(output_df.head())

        # Print Observability Report
        metrics_collector.print_report()

    except Exception as e:
        logger.critical(f"Pipeline Execution Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()