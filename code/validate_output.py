import os
import sys
import pandas as pd

# Reconfigure standard output to UTF-8 to prevent Windows CP1252 UnicodeEncodeErrors
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

OUTPUT_PATH = "dataset/output.csv"

ALLOWED_ACTIONS = {"notify", "digest", "mute"}
ALLOWED_TYPES = {
    "personal", "urgent", "event", "payment", "business_update",
    "promotion", "greeting", "forward", "spam", "scam", "unknown"
}

def validate():
    if not os.path.exists(OUTPUT_PATH):
        print("❌ Error: dataset/output.csv does not exist!")
        return False

    df = pd.read_csv(OUTPUT_PATH)
    print(f"Checking {len(df)} rows in {OUTPUT_PATH}...\n")

    errors = []

    # 1. Row count check
    if len(df) != 110:
        errors.append(f"Expected 110 rows, found {len(df)}.")

    # 2. Required columns check
    expected_cols = ["message_id", "action", "message_type", "reason", "confidence", "evidence_message_ids"]
    if list(df.columns) != expected_cols:
        errors.append(f"Column mismatch! Expected: {expected_cols}, got: {list(df.columns)}")

    # 3. Value validations
    for idx, row in df.iterrows():
        # Action check
        if row["action"] not in ALLOWED_ACTIONS:
            errors.append(f"Row {idx} ({row['message_id']}): Invalid action '{row['action']}'")

        # Message type check
        if row["message_type"] not in ALLOWED_TYPES:
            errors.append(f"Row {idx} ({row['message_id']}): Invalid message_type '{row['message_type']}'")

        # Confidence range check
        try:
            conf = float(row["confidence"])
            if not (0.0 <= conf <= 1.0):
                errors.append(f"Row {idx} ({row['message_id']}): Confidence {conf} out of bounds [0, 1]")
        except ValueError:
            errors.append(f"Row {idx} ({row['message_id']}): Non-numeric confidence value")

        # Check for empty mandatory text fields
        if pd.isna(row["reason"]) or str(row["reason"]).strip() == "":
            errors.append(f"Row {idx} ({row['message_id']}): Missing 'reason'")

    # 4. Summary
    if errors:
        print("❌ Validation Failed with errors:")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors.")
        return False
    else:
        print("✅ ALL SCHEMA CHECKS PASSED PERFECTLY!")
        print(f"- Total Predictions: {len(df)}")
        print(f"- Actions breakdown:\n{df['action'].value_counts().to_string()}")
        print(f"\n- Message types breakdown:\n{df['message_type'].value_counts().to_string()}")
        return True

if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)