import os
import pandas as pd
from loader import DataLoader
from context_builder import ContextBuilder
from retrieval import RetrievalEngine
from safety import SafetyEngine
from routing_agent import RoutingAgent

# Ensure path resolves correctly regardless of execution directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "dataset")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "output.csv")

def main():
    print("=== Starting Message Notification Router Pipeline ===")

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Initialize Data Loader
    loader = DataLoader(dataset_path=OUTPUT_DIR)
    data = loader.load_csv_files()
    messages_df = data["messages"]

    # 2. Initialize Core Engines
    context_builder = ContextBuilder(loader)
    retrieval_engine = RetrievalEngine(loader)
    safety_engine = SafetyEngine()
    routing_agent = RoutingAgent(retrieval_engine, safety_engine)

    results = []

    print(f"\nProcessing {len(messages_df)} incoming messages...")
    
    for idx, row in messages_df.iterrows():
        # Build relational context
        context = context_builder.build_context(row)

        # Get routing decision
        decision = routing_agent.route(context)

        # Format output record
        results.append({
            "message_id": row["message_id"],
            "action": decision["action"],
            "message_type": decision["message_type"],
            "reason": decision["reason"],
            "confidence": round(decision["confidence"], 2),
            "evidence_message_ids": decision["evidence_message_ids"]
        })

    # 3. Create DataFrame and Export output.csv
    output_df = pd.DataFrame(results)

    # Reorder explicitly to guarantee column order
    required_columns = ["message_id", "action", "message_type", "reason", "confidence", "evidence_message_ids"]
    output_df = output_df[required_columns]

    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"\n[SUCCESS] Successfully generated output.csv with {len(output_df)} predictions!")
    print(f"Saved to: {os.path.abspath(OUTPUT_PATH)}")
    print("\nFirst 5 predictions preview:")
    print(output_df.head())

if __name__ == "__main__":
    main()