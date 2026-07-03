# Graph Report - .  (2026-07-03)

## Corpus Check
- Corpus is ~15,007 words - fits in a single context window. You may not need a graph.

## Summary
- 237 nodes · 249 edges · 31 communities (22 shown, 9 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_LLM Pipeline & TTS Manager|LLM Pipeline & TTS Manager]]
- [[_COMMUNITY_Tauri Desktop Capabilities|Tauri Desktop Capabilities]]
- [[_COMMUNITY_Pronunciation Assessment & GOP|Pronunciation Assessment & GOP]]
- [[_COMMUNITY_Frontend WebSocket Audio Store|Frontend WebSocket Audio Store]]
- [[_COMMUNITY_Frontend Package Dependencies|Frontend Package Dependencies]]
- [[_COMMUNITY_ASR Speech-to-Text Processing|ASR Speech-to-Text Processing]]
- [[_COMMUNITY_Audio Processing Utilities|Audio Processing Utilities]]
- [[_COMMUNITY_Pipeline Data Models|Pipeline Data Models]]
- [[_COMMUNITY_Frontend TypeScript Configuration|Frontend TypeScript Configuration]]
- [[_COMMUNITY_App Architecture & Tauri Boot|App Architecture & Tauri Boot]]
- [[_COMMUNITY_Frontend NPM Scripts|Frontend NPM Scripts]]
- [[_COMMUNITY_Backend Settings Configuration|Backend Settings Configuration]]
- [[_COMMUNITY_Graphify Integration Rules|Graphify Integration Rules]]
- [[_COMMUNITY_Backend Startup Launcher|Backend Startup Launcher]]
- [[_COMMUNITY_Frontend Layout & Assets|Frontend Layout & Assets]]
- [[_COMMUNITY_OpenCode Configuration Schema|OpenCode Configuration Schema]]
- [[_COMMUNITY_OpenCode Package Dependencies|OpenCode Package Dependencies]]
- [[_COMMUNITY_Svelte Application Config|Svelte Application Config]]
- [[_COMMUNITY_Svelte Route Entry Page|Svelte Route Entry Page]]
- [[_COMMUNITY_Empty Response Handling|Empty Response Handling]]
- [[_COMMUNITY_Global Backend Config|Global Backend Config]]
- [[_COMMUNITY_LLM System Prompt Config|LLM System Prompt Config]]

## God Nodes (most connected - your core abstractions)
1. `WhisperASR` - 12 edges
2. `compilerOptions` - 11 edges
3. `LLMManager` - 10 edges
4. `GOPScorer` - 8 edges
5. `TTSManager` - 8 edges
6. `lifespan()` - 8 edges
7. `scripts` - 7 edges
8. `websocket_audio()` - 6 edges
9. `startRecording()` - 6 edges
10. `ASR-LLM-TTS pipeline execution helper` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Tauri + SvelteKit Frontend` --conceptually_related_to--> `connectWebSocket()`  [INFERRED]
  docs/architecture.md → frontend/src/lib/stores/audioStore.ts
- `Frontend WebSocket Logic` --conceptually_related_to--> `connectWebSocket()`  [INFERRED]
  docs/configuration.md → frontend/src/lib/stores/audioStore.ts
- `Tauri + SvelteKit Frontend` --conceptually_related_to--> `run()`  [INFERRED]
  docs/architecture.md → frontend/src-tauri/src/lib.rs
- `Graphify rules configuration` --semantically_similar_to--> `Graphify Instructions in AGENTS.md`  [INFERRED] [semantically similar]
  .agents/rules/graphify.md → AGENTS.md
- `Graphify OpenCode Plugin Hook` --conceptually_related_to--> `Graphify rules configuration`  [INFERRED]
  .opencode/plugins/graphify.js → .agents/rules/graphify.md

## Import Cycles
- 1-file cycle: `backend/app/main.py -> backend/app/main.py`

## Hyperedges (group relationships)
- **ASR-LLM-TTS Conversational Pipeline Flow** — app_main__run_pipeline, ai_pipeline_asr_whisperasr, ai_pipeline_llm_llmmanager, ai_pipeline_tts_ttsmanager [EXTRACTED 1.00]
- **Goodness-of-Pronunciation Assessment Flow** — ai_pipeline_pronunciation_forcedaligner, ai_pipeline_pronunciation_gopscorer, ai_pipeline_pronunciation_calculate_gop [INFERRED 0.95]
- **Graphify Knowledge Graph Integration and Rules** — agents_graphify, rules_graphify_rules, workflows_graphify_workflow, plugins_graphify_plugin [INFERRED 0.95]
- **Tauri Desktop Application Bootstrap Flow** — src_main_main, src_lib_run, src_tauri_tauri_conf [INFERRED 0.85]
- **Audio Recording and Streaming Control Flow** — stores_audiostore_togglerecording, stores_audiostore_startrecording, stores_audiostore_stoprecording, routes__page_handletoggle [INFERRED 0.95]

## Communities (31 total, 9 thin omitted)

### Community 0 - "LLM Pipeline & TTS Manager"
Cohesion: 0.08
Nodes (25): LLMManager, LLM (Large Language Model) Module =================================== Conversati, Reset the conversation context., Manages conversation with a local LLM via LM Studio's     OpenAI-compatible API., Send the user's text to the LLM and return the assistant's reply.          The c, TTS (Text-to-Speech) Module ============================= MVP implementation usi, Text-to-Speech manager using edge-tts.      Parameters     ----------     voice, Convert text to speech and return WAV-like audio bytes.          Parameters (+17 more)

### Community 1 - "Tauri Desktop Capabilities"
Cohesion: 0.08
Nodes (24): description, identifier, permissions, $schema, windows, debugApplicationIdSuffix, app, security (+16 more)

### Community 2 - "Pronunciation Assessment & GOP"
Cohesion: 0.10
Nodes (17): calculate_gop(), ForcedAligner, GOPScorer, Pronunciation Assessment Module ================================= Stubs for Forc, # TODO: Implement GOP scoring, High-level function: run forced alignment on raw audio bytes.      Parameters, # TODO: Implement Montreal Forced Aligner here, High-level function: compute Goodness-of-Pronunciation scores.      Parameters (+9 more)

### Community 3 - "Frontend WebSocket Audio Store"
Cohesion: 0.13
Nodes (18): Frontend WebSocket Logic, handleToggle, chunkPromises, ConnectionStatus, connectWebSocket(), disconnectWebSocket(), isRecording, latestLLMResponse (+10 more)

### Community 4 - "Frontend Package Dependencies"
Cohesion: 0.10
Nodes (19): dependencies, @tauri-apps/api, devDependencies, svelte, svelte-check, @sveltejs/adapter-auto, @sveltejs/kit, @sveltejs/vite-plugin-svelte (+11 more)

### Community 5 - "ASR Speech-to-Text Processing"
Cohesion: 0.14
Nodes (9): ASR (Automatic Speech Recognition) Module ======================================, Synchronous transcription (runs on the thread pool).          Parameters, Decode raw audio bytes and transcribe asynchronously.          This method decod, GPU-accelerated ASR engine backed by faster-whisper (CTranslate2).      Paramete, Load the faster-whisper model into VRAM.         Call once at application startu, Release model resources and free VRAM., Decode WebM/Opus audio bytes (from MediaRecorder) into a         16 kHz mono flo, WhisperASR (+1 more)

### Community 6 - "Audio Processing Utilities"
Cohesion: 0.18
Nodes (11): ndarray, compute_energy(), extract_pitch_contour(), Audio processing utilities. Stubs for librosa / parselmouth helper functions use, Resample raw audio bytes to the target sample rate.      Parameters     --------, Extract the fundamental frequency (F0) contour from an audio buffer     using Pa, # TODO: Implement pitch extraction with parselmouth, Compute short-time energy of an audio signal.      Parameters     ---------- (+3 more)

### Community 7 - "Pipeline Data Models"
Cohesion: 0.21
Nodes (12): BaseModel, AudioChunkMeta, GOPResult, PhonemeScore, PipelineResponse, Pydantic schemas for request / response validation., Metadata that can optionally accompany an audio chunk., Result returned by the ASR module. (+4 more)

### Community 8 - "Frontend TypeScript Configuration"
Cohesion: 0.15
Nodes (12): compilerOptions, allowJs, checkJs, esModuleInterop, forceConsistentCasingInFileNames, moduleResolution, resolveJsonModule, rewriteRelativeImportExtensions (+4 more)

### Community 9 - "App Architecture & Tauri Boot"
Cohesion: 0.22
Nodes (8): FastAPI Backend, Conversational Pipeline Flow, Tauri + SvelteKit Frontend, Split Architecture, greet(), run(), main(), String

### Community 10 - "Frontend NPM Scripts"
Cohesion: 0.29
Nodes (7): scripts, build, check, check:watch, dev, prepare, preview

### Community 11 - "Backend Settings Configuration"
Cohesion: 0.33
Nodes (5): BaseSettings, Config, Application configuration. Centralises environment variables and system-level se, Global application settings loaded from environment or defaults., Settings

### Community 12 - "Graphify Integration Rules"
Cohesion: 0.40
Nodes (5): Graphify Instructions in AGENTS.md, OpenCode Plugin Configurations, Graphify OpenCode Plugin Hook, Graphify rules configuration, Graphify workflow guide

## Knowledge Gaps
- **80 isolated node(s):** `$schema`, `plugin`, `@opencode-ai/plugin`, `Config`, `start.sh script` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ASR-LLM-TTS pipeline execution helper` connect `LLM Pipeline & TTS Manager` to `ASR Speech-to-Text Processing`, `Pipeline Data Models`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Why does `PipelineResponse` connect `Pipeline Data Models` to `LLM Pipeline & TTS Manager`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `GOPScorer` connect `Pronunciation Assessment & GOP` to `Audio Processing Utilities`, `Pipeline Data Models`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `WhisperASR` (e.g. with `FastAPI` and `WebSocket`) actually correct?**
  _`WhisperASR` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `LLMManager` (e.g. with `FastAPI` and `WebSocket`) actually correct?**
  _`LLMManager` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `GOPScorer` (e.g. with `resample_audio()` and `GOPResult`) actually correct?**
  _`GOPScorer` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `plugin`, `@opencode-ai/plugin` to the rest of the system?**
  _126 weakly-connected nodes found - possible documentation gaps or missing edges._