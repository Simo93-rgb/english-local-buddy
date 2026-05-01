# App Architecture

English Buddy is built with a split architecture: a fast, lightweight **Tauri + SvelteKit** frontend, and a heavy-lifting **FastAPI Python** backend that processes the AI pipeline.

## High-Level System Architecture

```mermaid
graph TD
    subgraph Frontend [Tauri + SvelteKit Frontend]
        UI[User Interface]
        AudioStore[audioStore.ts]
        Recorder[MediaRecorder]
        Player[HTML5 Audio]
    end

    subgraph Backend [FastAPI Backend]
        WS[WebSocket /ws/audio]
        ASR[Whisper ASR Engine]
        LLM[LLM Manager]
        TTS[Edge-TTS Engine]
    end

    subgraph External [External Services]
        LMStudio[LM Studio Local API]
    end

    UI -->|Record| AudioStore
    AudioStore -->|Start| Recorder
    Recorder -.->|WebM Audio Chunks| WS
    AudioStore -->|STOP Signal| WS

    WS -->|Bytes| ASR
    ASR -->|Transcription Text| LLM
    LLM -->|Prompt + Context| LMStudio
    LMStudio -->|Text Response| LLM
    LLM -->|Text Response| TTS
    TTS -->|MP3 Audio Bytes| WS

    WS -.->|Base64 MP3 + Status JSON| AudioStore
    AudioStore -->|Play| Player
    AudioStore -->|Render text| UI
```

## Conversational Pipeline Flow

This diagram illustrates the timing and status updates during a single conversational turn.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant FastAPI
    participant Whisper
    participant LMStudio
    participant EdgeTTS

    User->>Frontend: Clicks "Record"
    Frontend->>FastAPI: Connects to /ws/audio (if not already)
    Note over User,Frontend: User speaks...
    Frontend-->>FastAPI: Streams binary chunks (WebM/Opus)
    User->>Frontend: Clicks "Stop"
    Frontend->>FastAPI: Sends "STOP" message
    FastAPI->>Frontend: Status: "transcribing"
    
    FastAPI->>Whisper: Transcribe Buffer
    Whisper-->>FastAPI: Returns Text (e.g., "Hello")
    FastAPI->>Frontend: Sends transcription JSON

    FastAPI->>Frontend: Status: "thinking"
    FastAPI->>LMStudio: Chat Completion Request (History + "Hello")
    LMStudio-->>FastAPI: Returns LLM Reply
    FastAPI->>Frontend: Sends LLM text JSON
    
    FastAPI->>Frontend: Status: "speaking"
    FastAPI->>EdgeTTS: Generate speech from text
    EdgeTTS-->>FastAPI: Returns MP3 Bytes
    
    FastAPI->>Frontend: Sends Base64 Audio JSON
    Frontend->>User: Auto-plays Audio
    FastAPI->>Frontend: Status: "done"
```
