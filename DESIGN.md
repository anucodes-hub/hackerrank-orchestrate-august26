# AI Notification Router

## Objective

Route WhatsApp messages into:

- notify
- digest
- mute

## Pipeline

1. Read message
2. Load user context
3. Load sender context
4. Load history
5. Process media
6. Detect scam/safety
7. Personalize
8. Decide priority
9. Save output.csv

## Modules

loader.py
media_processor.py
context_builder.py
risk_detector.py
priority_router.py
output_writer.py
main.py