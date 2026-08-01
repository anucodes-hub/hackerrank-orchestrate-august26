# WhatsApp Notification Router Setup & Running Guide

This guide describes how to set up, configure, and execute the WhatsApp Notification Router starting from a fresh environment.

---

## 1. Prerequisites
- **Python**: Version `3.10` or `3.11` (specifically tested on `3.10.11` and `3.11.x`).
- **Package Manager**: `pip` (included by default with Python installer).
- **Environment**: Terminal shell (Command Prompt / PowerShell for Windows; Bash / Zsh for macOS and Linux).
- **Audio Decoding (Optional)**: `ffmpeg` (required by `pydub` only if processing raw audio files natively; otherwise, Gemini handles audio uploads directly).

---

## 2. Setting Up the Environment

### Step 2.1: Clone the Repository
Clone the repository and enter the directory:
```bash
git clone <repository_url>
cd hackerrank-orchestrate-august26
```

### Step 2.2: Create a Virtual Environment
Choose the commands below based on your operating system:

#### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2.3: Install Dependencies
Install all required libraries using `pip`:
```bash
pip install -r requirements.txt
```
*(If no `requirements.txt` is present, install directly: `pip install pandas pillow google-generativeai pydub`)*

---

## 3. Configuration & Environment Variables

### Step 3.1: Create a `.env` File
Create a `.env` file in the project root directory.

```ini
# .env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 3.2: Obtain a Gemini API Key
1. Go to the [Google AI Studio Console](https://aistudio.google.com/).
2. Log in with your Google account.
3. Click on **Create API Key**.
4. Select or create a project, then copy the generated API key.
5. Paste it in your `.env` file replacing `your_gemini_api_key_here`.

### Step 3.3: Verify Environment Variables
Verify your environment configuration before running:

#### Windows (PowerShell)
```powershell
# Load variables manually from .env if needed
$env:GEMINI_API_KEY="your_actual_key_here"
```

#### macOS / Linux
```bash
export GEMINI_API_KEY="your_actual_key_here"
```

---

## 4. Running the Code

### Step 4.1: Execute the Pipeline
Run the main notification router pipeline:
```bash
python code/main.py
```
This script runs the routing logic over every incoming message in `dataset/messages.csv` and outputs a processed predictions file at `dataset/output.csv`.

### Step 4.2: Execute Output Validation
Run the schema validator to ensure the output matches the required hackathon format:
```bash
# On Windows PowerShell
$env:PYTHONIOENCODING="utf-8"; python code/validate_output.py

# On macOS / Linux / Bash
PYTHONIOENCODING=utf-8 python code/validate_output.py
```

---

## 5. Troubleshooting & Debugging

- **Error: 429 Rate Limit Exceeded**:
  - **Why**: You are using Gemini API free tier limits (which has limits like 15 RPM).
  - **Mitigation**: The system detects this error and automatically falls back to local Dynamic scoring weights gracefully without stopping the pipeline execution.
- **Error: UnicodeEncodeError on Output Validation**:
  - **Why**: PowerShell / Windows Terminal default encoding mismatch.
  - **Mitigation**: Always run validation with the env variable `$env:PYTHONIOENCODING="utf-8"` set.
- **Error: Missing Media File Warnings**:
  - **Why**: Specific image or audio file path missing in `dataset/media/`.
  - **Mitigation**: System automatically catches file paths and falls back to descriptions stored in `images.csv` or `voice_notes.csv`.
