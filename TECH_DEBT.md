# Technical Debt & Software Engineering Observations

Questo documento censisce le imperfezioni architetturali e i margini di miglioramento ingegneristico riscontrati nel codebase, annotati per interventi futuri senza bloccare lo sviluppo funzionale corrente.

---

### 1. Hardcoding della Lingua e Parametri ASR (`backend/app/ai_pipeline/asr.py`)
- **Problema**: Nel metodo `_transcribe_sync`, il parametro `language="en"` è hardcoded, impedendo a Whisper di trascrivere altre lingue o di utilizzare il rilevamento automatico, anche in presenza di modelli multilingua (`medium`, `large-v3`).
- **Impatto**: Limita l'estensibilità a scenari multilingua o tandem linguistico.

### 2. Duplicazione e Hardcoding delle Chiavi API (`llm.py`, `history_manager.py`)
- **Problema**: Entrambi i moduli istanziano `AsyncOpenAI` cablando `api_key="lm-studio"` direttamente nel codice sorgente invece di attingere a una configurazione centralizzata (`settings.LLM_API_KEY`).
- **Impatto**: Modifiche a provider LLM (es. Unsloth, Ollama, OpenAI) richiedono interventi su più file e aumentano il rischio di regressioni.

### 3. Prompt di Sistema Cablati nel Codice Python (`llm.py`, `history_manager.py`)
- **Problema**: I prompt di sistema (`SYSTEM_PROMPT`, `ASSESSOR_SYSTEM_PROMPT`) sono definiti come stringhe statiche multiriga nei file `.py`.
- **Impatto**: Difficoltà per formatori e non sviluppatori nell'aggiornare o raffinare il comportamento pedagogico del bot senza modificare il codice applicativo.

### 4. Concorrenza ASR a Singolo Worker Globale (`asr.py`)
- **Problema**: `_executor = ThreadPoolExecutor(max_workers=1)` serializza le inferenze di trascrizione su un unico thread globale.
- **Impatto**: In presenza di sessioni concorrenti o audio prolungati, si creano colli di bottiglia e latenza accumulata.

### 5. Gestione Asincrona "Fire-and-Forget" dei Task di Sessione (`main.py`)
- **Problema**: All'evento di disconnect del WebSocket, il report di fine sessione viene lanciato con `asyncio.create_task(...)` senza tracciamento o gestione strutturata della cancellazione.
- **Impatto**: In caso di spegnimento improvviso del server, i task pendenti possono essere terminati a metà scrittura.

### 6. Assenza di Reconnection Policy nel Frontend (`audioStore.ts`)
- **Problema**: In caso di chiusura imprevista del socket (es. riavvio backend o micro-disconnessione di rete), il client imposta semplicemente lo stato su `disconnected` senza tentativi di riconnessione con backoff esponenziale.
- **Impatto**: L'utente deve ricaricare la pagina o riavviare la sessione manualmente.

### 7. Dipendenza dalla Decodifica WebM/Opus via `pydub` (`asr.py`)
- **Problema**: Il browser invia container WebM/Opus, che costringe il backend a tentare `soundfile` e poi ricorrere a `pydub` (processo `ffmpeg` esterno).
- **Impatto**: Overhead di CPU e latenza per ogni chunk audio finalizzato.
