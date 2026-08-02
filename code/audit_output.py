import os
import sys
import pandas as pd

# Reconfigure stdout to UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "output.csv")

def audit():
    if not os.path.exists(OUTPUT_PATH):
        print(f"❌ Error: {OUTPUT_PATH} does not exist!")
        return

    df = pd.read_csv(OUTPUT_PATH)
    total_rows = len(df)

    print("====================================================")
    print("               OUTPUT QUALITY AUDIT REPORT          ")
    print("====================================================")
    print(f"Total Prediction Rows:       {total_rows}")

    # 1. Reason Diversity & Frequency Analysis
    unique_reasons = df["reason"].nunique()
    reason_counts = df["reason"].value_counts()
    most_common_reason_cnt = reason_counts.iloc[0] if not reason_counts.empty else 0
    most_common_pct = round((most_common_reason_cnt / total_rows) * 100, 2)
    diversity_score = round((unique_reasons / total_rows) * 100, 2)

    print(f"Unique Reason Strings:       {unique_reasons} / {total_rows}")
    print(f"Reason Diversity Score:      {diversity_score}%")
    print(f"Max Single Reason Share:     {most_common_pct}% (Limit: <= 5.0%)")

    # 2. Confidence Variance & Distribution
    conf_series = df["confidence"].astype(float)
    conf_mean = round(conf_series.mean(), 3)
    conf_std = round(conf_series.std(), 3)
    conf_min = round(conf_series.min(), 3)
    conf_max = round(conf_series.max(), 3)
    unique_conf_values = conf_series.nunique()

    print("\nConfidence Distribution:")
    print(f"  - Mean Confidence:         {conf_mean}")
    print(f"  - Std Deviation:           {conf_std}")
    print(f"  - Min / Max Confidence:    {conf_min} / {conf_max}")
    print(f"  - Unique Confidence Values: {unique_conf_values}")

    # 3. Action & Message Type Breakdown
    print("\nRouting Action Distribution:")
    for act, cnt in df["action"].value_counts().items():
        print(f"  - {act.upper():<8}: {cnt} ({round((cnt/total_rows)*100, 1)}%)")

    print("\nMessage Types Breakdown:")
    for mt, cnt in df["message_type"].value_counts().items():
        print(f"  - {mt:<16}: {cnt}")

    print("\nTop 3 Most Frequent Reason Explanations:")
    for idx, (reason_str, cnt) in enumerate(reason_counts.head(3).items(), 1):
        pct = round((cnt / total_rows) * 100, 1)
        print(f"  {idx}. [{cnt} rows | {pct}%] \"{reason_str}\"")

    print("\n====================================================")
    if most_common_pct <= 5.0:
        print("✅ DIVERSITY AUDIT PASSED PERFECTLY! (No template >5%)")
    else:
        print(f"⚠️ DIVERSITY NOTICE: Most common reason is {most_common_pct}% (>5.0%).")
    print("====================================================\n")

if __name__ == "__main__":
    audit()
