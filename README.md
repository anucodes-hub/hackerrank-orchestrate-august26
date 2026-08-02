# HackerRank Orchestrate - Message Notification Router

An enterprise-grade, multimodal, AI-powered **Message Notification Router** for WhatsApp. It analyzes incoming text messages, image posters/screenshots, and voice notes alongside rich historical interaction context, user profiles, quiet hours, and business history to decide whether each message should interrupt the user (`notify`), be batched (`digest`), or be muted (`mute`).

---

## 🌟 Key System Capabilities

- **Real Multimodal Analysis**: Uses Gemini Vision for OCR/poster/screenshot/receipt analysis and Gemini Audio API for voice note speech transcription & tone detection.
- **Robust Resilience & Caching**: Disk-backed media cache (`dataset/media_cache.json`) with seamless fallback to dynamic modular scoring engine on network error/quota limits.
- **Multi-Tier Safety Guardrails**: Overriding safety engine detecting phishing links, URL reputation, prompt injection/jailbreaks, unverified/reported business senders, and muted group rules.
- **Modular Dynamic Scoring Engine**: Calculates modular scores for urgency, trust, user engagement, notification fatigue, business history, and forwarding penalties.
- **Observability & Structured Metrics**: Built-in metrics collector tracking execution latency, API success rates, cache hits, routing breakdown, top safety triggers, and personalization signals.
- **Zero Hardcoding**: All weights, thresholds, retry parameters, model names, and scam checklists are fully configurable via `.env` and `code/config.py`.

---

## 📁 Repository Layout

```text
.
├── .env.example                      # Template environment configuration
├── AGENTS.md                         # Coding conventions & transcript logging
├── ARCHITECTURE.md                   # System architecture & 5 Mermaid flow diagrams
├── CONFIGURATION.md                  # Comprehensive configuration reference guide
├── DESIGN.md                         # Design blueprint
├── README.md                         # Main repository documentation
├── SETUP.md                          # Quickstart, installation, and testing guide
├── code/
│   ├── config.py                     # Centralized configuration & environment loader
│   ├── context_builder.py            # Unified semantic context aggregator
│   ├── loader.py                     # Pre-indexed dataset loader & user stats calculator
│   ├── main.py                       # Main pipeline driver & CLI entry point
│   ├── media_processor.py            # Gemini multimodal OCR & voice note handler
│   ├── observability.py              # Metrics collector & structured observability reporter
│   ├── retrieval.py                  # Historical evidence message ID finder
│   ├── risk_detector.py              # Safety engine wrapper
│   ├── routing_agent.py              # Primary routing agent with LLM & fallback scoring
│   ├── safety.py                     # First-pass safety & phishing guardrails engine
│   ├── scoring_engine.py             # Dynamic modular scoring engine
│   ├── utils.py                      # Utilities, URL regex domain parser, retry decorator
│   ├── validate_output.py            # Predictions CSV schema validator
│   └── tests/
│       └── test_suite.py             # Automated unit & integration test suite
└── dataset/
    ├── messages.csv                  # 110 incoming messages to route
    ├── output.csv                    # Final prediction output file
    ├── media_cache.json              # Disk cache for media processing
    └── media/                        # Image and audio files
```

---

## 🚀 Quickstart

1. Configure environment:
   ```bash
   cp .env.example .env
   ```

2. Run automated test suite:
   ```bash
   python code/tests/test_suite.py
   ```

3. Run notification router pipeline:
   ```bash
   python code/main.py
   ```

4. Validate output schema:
   ```bash
   python code/validate_output.py
   ```
