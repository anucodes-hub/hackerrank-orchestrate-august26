# Architecture Specification - Message Notification Router

This document details the system design, agent interactions, data pipelines, sequence flows, and decision-making logic of the AI-powered WhatsApp Message Notification Router.

---

## 1. System Architecture Diagram

```mermaid
flowchart TB
    subgraph Ingestion["1. Data Ingestion & Pre-Indexing"]
        CSV_M["messages.csv"]
        CSV_H["message_history.csv"]
        CSV_E["message_events.csv"]
        CSV_M_M["images.csv / voice_notes.csv"]
        DL["DataLoader (loader.py)"]
        CSV_M --> DL
        CSV_H --> DL
        CSV_E --> DL
        CSV_M_M --> DL
    end

    subgraph Multimodal["2. Multimodal Processing"]
        MP["MediaProcessor (media_processor.py)"]
        MC["Disk Cache (media_cache.json)"]
        GEM_V["Gemini Vision API"]
        GEM_A["Gemini Audio API"]
        DL --> MP
        MP <--> MC
        MP -->|Image OCR| GEM_V
        MP -->|Audio STT| GEM_A
    end

    subgraph UnifiedContext["3. Context Aggregation"]
        CB["ContextBuilder (context_builder.py)"]
        MP --> CB
        DL --> CB
    end

    subgraph Intelligence["4. Safety & Reasoning Engine"]
        SE["SafetyEngine (safety.py)"]
        RE["RetrievalEngine (retrieval.py)"]
        SCE["ScoringEngine (scoring_engine.py)"]
        RA["RoutingAgent (routing_agent.py)"]
        GEM_L["Gemini Routing LLM"]
        
        CB --> SE
        CB --> RE
        CB --> RA
        SE -->|Safety Override| RA
        RE -->|Evidence IDs| RA
        RA -->|Primary Reasoning| GEM_L
        RA -->|Dynamic Fallback| SCE
    end

    subgraph Output["5. Output & Observability"]
        OUT["dataset/output.csv"]
        MET["MetricsCollector (observability.py)"]
        VAL["Validator (validate_output.py)"]
        
        RA --> OUT
        RA --> MET
        OUT --> VAL
    end
```

---

## 2. Agent Interaction Diagram

```mermaid
graph TD
    UserMsg["Incoming Message Row"] --> Main["Main Driver (main.py)"]
    Main --> CB["ContextBuilder"]
    CB --> MP["MediaProcessor"]
    MP -->|Check Cache / Call Gemini| GeminiMedia["Gemini Multimodal API"]
    CB --> UnifiedCtx["Unified Semantic Context Object"]
    UnifiedCtx --> RA["RoutingAgent"]
    
    RA --> SE["SafetyEngine Guardrails"]
    SE -->|Safety Trigger Detected| MuteOverride["Force Action: mute + scam"]
    
    RA --> RE["RetrievalEngine"]
    RE -->|Context Matches & Interactions| EvidenceIDs["Evidence Message IDs"]
    
    RA -->|If API Available| GeminiLLM["Gemini LLM Router"]
    RA -->|If API Quota / Offline| ScoringEng["ScoringEngine (Dynamic Scores)"]
    
    GeminiLLM --> FinalDecision["Routing Decision JSON"]
    ScoringEng --> FinalDecision
    MuteOverride --> FinalDecision
    
    FinalDecision --> Main
    Main --> CSVWriter["output.csv Export"]
    Main --> ObsReport["Observability Report"]
```

---

## 3. Processing Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Main as main.py
    participant Loader as DataLoader
    participant MP as MediaProcessor
    participant CB as ContextBuilder
    participant Safety as SafetyEngine
    participant Retrieval as RetrievalEngine
    participant Agent as RoutingAgent
    participant LLM as Gemini API
    participant Score as ScoringEngine
    participant Obs as MetricsCollector

    Main->>Loader: load_csv_files()
    Loader-->>Main: Parsed DataFrames & Hash Indexes
    loop For Each Incoming Message
        Main->>CB: build_context(row)
        CB->>MP: process_media(media_type, media_id)
        alt Cache Hit
            MP-->>CB: Cached OCR / Speech Transcript
        else Cache Miss / Call Gemini
            MP->>LLM: generate_content(prompt + image/audio)
            LLM-->>MP: Extracted Text / Transcript
            MP-->>CB: Multimodal Extracted Text
        end
        CB-->>Main: Unified Semantic Context Object
        Main->>Agent: route(context)
        Agent->>Safety: evaluate(context)
        alt Safety Trigger (Phishing / Injection / Spam)
            Safety-->>Agent: Override Decision (mute, scam)
        else Safe Message
            Agent->>Retrieval: find_evidence(message, user_id)
            Retrieval-->>Agent: Semicolon-Separated Evidence IDs
            alt Gemini API Available
                Agent->>LLM: _route_llm(unified_text, context)
                LLM-->>Agent: Structured JSON Decision
            else Quota Exceeded / Fallback
                Agent->>Score: compute_scores(context)
                Score-->>Agent: Dynamic Priority Decision
            end
        end
        Agent->>Obs: record_decision(...)
        Agent-->>Main: Decision Record
    end
    Main->>Main: Export output.csv
    Main->>Obs: print_report()
```

---

## 4. Data Flow Diagram

```mermaid
flowchart LR
    subgraph Inputs
        M["messages.csv"]
        U["users.csv"]
        G["groups.csv"]
        B["business_accounts.csv"]
        H["message_history.csv"]
        E["message_events.csv"]
        MEDIA["media/images & audio"]
    end

    subgraph ProcessingPipeline["Core Pipeline"]
        direction TB
        F1["Pre-Indexing & Stats Calculation"]
        F2["Media Extraction & Multimodal Transcripts"]
        F3["Unified Context Construction"]
        F4["Safety & Guardrail Checks"]
        F5["Historical Evidence Retrieval"]
        F6["Priority & Modular Scoring Engine"]
    end

    subgraph OutputData
        O["dataset/output.csv"]
        LOG["Console & Observability Logs"]
    end

    M & U & G & B & H & E --> F1
    MEDIA --> F2
    F1 & F2 --> F3
    F3 --> F4
    F3 --> F5
    F4 & F5 --> F6
    F6 --> O
    F6 --> LOG
```

---

## 5. Decision Flow Diagram

```mermaid
flowchart TD
    Start["Incoming Message"] --> SafetyCheck{"Safety Check (safety.py)"}
    
    SafetyCheck -->|Prompt Injection / Phishing Domain / Scam Kw| MuteScam["Action: MUTE<br>Type: scam / spam<br>Conf: 0.95 - 0.99"]
    
    SafetyCheck -->|Safe Content| MutedGroupCheck{"Group Muted & No Direct @Mention?"}
    
    MutedGroupCheck -->|Yes| MuteGroup["Action: MUTE<br>Type: personal / unknown<br>Conf: 0.95"]
    
    MutedGroupCheck -->|No| PriorityRouting{"Gemini API / Scoring Engine"}
    
    PriorityRouting --> CalcScores["Calculate Urgency, Trust, Engagement,<br>Fatigue, Business & Forward Scores"]
    
    CalcScores --> ScoreCheck{"Final Priority Score"}
    
    ScoreCheck -->|Score >= 0.70| NotifyAction["Action: NOTIFY<br>Type: urgent / payment / personal<br>Conf: Dynamic Score"]
    ScoreCheck -->|0.35 < Score < 0.70| DigestAction["Action: DIGEST<br>Type: event / business_update / promotion<br>Conf: Dynamic Score"]
    ScoreCheck -->|Score <= 0.35| MuteAction["Action: MUTE<br>Type: promotion / forward / greeting<br>Conf: Dynamic Score"]
```
