# Setup & Execution Guide - Message Notification Router

This document provides complete instructions for setting up the environment, installing dependencies, configuring environment variables, running tests, and executing the pipeline.

---

## 1. Prerequisites

- Python 3.10 or higher
- Terminal shell (PowerShell or Bash)

---

## 2. Environment Setup & Installation

1. Clone or navigate to the repository directory:
   ```bash
   cd hackerrank-orchestrate-august26
   ```

2. Copy the environment configuration template:
   ```bash
   cp .env.example .env
   ```

3. Open `.env` and set your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   MODEL_NAME=gemini-2.0-flash
   DEBUG=false
   ENABLE_MEDIA_CACHE=true
   ```

4. Install required Python packages:
   ```bash
   pip install python-dotenv pandas pillow google-generativeai
   ```

---

## 3. Running Automated Tests

Run the automated test suite to verify module health, config loading, safety guardrails, scoring engine, and media caching:

```bash
python code/tests/test_suite.py
```

Expected output:
```text
Ran 8 tests in 0.059s
OK
```

---

## 4. Running the Main Notification Router Pipeline

Execute the full pipeline on `dataset/messages.csv` to generate `dataset/output.csv`:

```bash
python code/main.py
```

For verbose step-by-step debug logging:
```bash
python code/main.py --debug
```

---

## 5. Validating Predictions Output

Run the official schema validator to verify row counts, column alignment, enum correctness, and confidence ranges:

```bash
python code/validate_output.py
```

Expected output:
```text
Checking 110 rows in dataset/output.csv...
✅ ALL SCHEMA CHECKS PASSED PERFECTLY!
```
