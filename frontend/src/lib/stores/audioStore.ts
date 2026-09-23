/**
 * Audio Store – WebSocket & MediaRecorder state management
 * =========================================================
 * Handles the full conversational loop:
 *   1. Capture mic audio → stream binary chunks to backend
 *   2. Send "STOP" → backend runs ASR → LLM → TTS
 *   3. Receive status updates, transcription, LLM text, and TTS audio
 *   4. Auto-play the TTS audio response
 */

import { writable, derived, get } from 'svelte/store';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ToneAssessmentItem {
	syllable: string;
	expected_tone: number;
	detected_tone: number;
	is_correct: boolean;
	pitch_contour?: number[];
	feedback: string;
}

export interface ToneAnalysisData {
	overall_accuracy: number;
	tones: ToneAssessmentItem[];
	summary: string;
}

export interface WSMessage {
	type?: string;
	status: string;
	transcription?: string;
	confidence?: number;
	language?: string;
	segments?: Array<{ start: number; end: number; text: string; avg_logprob: number }>;
	gop_score?: number | null;
	tone_analysis?: ToneAnalysisData;
	llm_text?: string;
	audio_b64?: string;
	audio_format?: string;
	message?: string;
	timestamp: number;
}

type ConnectionStatus =
	| 'disconnected'
	| 'connecting'
	| 'connected'
	| 'transcribing'
	| 'thinking'
	| 'speaking'
	| 'error';

export type ChineseLevel = 'beginner_tutor' | 'intermediate' | 'advanced_buddy';
export type AppMode = 'tutor' | 'tts_studio';

export interface TTSGenerateResult {
	status: string;
	audio_b64: string;
	audio_format: string;
	voice: string;
	rate: string;
	pitch: string;
	processed_text: string;
	size_bytes: number;
	filename: string;
}

// ---------------------------------------------------------------------------
// Stores
// ---------------------------------------------------------------------------

/** Current application mode: interactive conversational tutor or dedicated TTS Studio */
export const currentMode = writable<AppMode>('tutor');

/** Whether the microphone is currently recording */
export const isRecording = writable<boolean>(false);

/** WebSocket connection status */
export const connectionStatus = writable<ConnectionStatus>('disconnected');

/** Per-language message logs to ensure complete conversation isolation */
const enMessageLog = writable<WSMessage[]>([]);
const zhMessageLog = writable<WSMessage[]>([]);

/** Per-language latest transcription */
const enLatestTranscription = writable<string>('');
const zhLatestTranscription = writable<string>('');

/** Per-language latest LLM response */
const enLatestLLMResponse = writable<string>('');
const zhLatestLLMResponse = writable<string>('');

/** Current learning language */
export const currentLanguage = writable<'en' | 'zh'>('en');

/** Current Chinese learning level */
export const chineseLevel = writable<ChineseLevel>('beginner_tutor');

/** The latest acoustic tone assessment result */
export const latestToneAnalysis = writable<ToneAnalysisData | null>(null);

/** Latest synthesized audio payload in base64 (for playback and download) */
export const latestAudioB64 = writable<{ b64: string; format: string; text: string; language: 'en' | 'zh' } | null>(null);

/** Log of messages received from the backend for the active language */
export const messageLog = derived([currentLanguage, enMessageLog, zhMessageLog], ([$lang, $en, $zh]) =>
	$lang === 'zh' ? $zh : $en
);

/** The latest transcription text for the active language */
export const latestTranscription = derived([currentLanguage, enLatestTranscription, zhLatestTranscription], ([$lang, $en, $zh]) =>
	$lang === 'zh' ? $zh : $en
);

/** The latest LLM response text for the active language */
export const latestLLMResponse = derived([currentLanguage, enLatestLLMResponse, zhLatestLLMResponse], ([$lang, $en, $zh]) =>
	$lang === 'zh' ? $zh : $en
);

/** The latest message from the backend */
export const latestMessage = derived(messageLog, ($log) =>
	$log.length > 0 ? $log[$log.length - 1] : null
);

// ---------------------------------------------------------------------------
// Internal state
// ---------------------------------------------------------------------------

let ws: WebSocket | null = null;
let mediaRecorder: MediaRecorder | null = null;
let mediaStream: MediaStream | null = null;
let chunkPromises: Promise<void>[] = [];

// WS_URL is evaluated dynamically when connectWebSocket is called
let WS_URL = 'ws://localhost:8000/ws/audio';
const CHUNK_INTERVAL_MS = 250;

// ---------------------------------------------------------------------------
// Audio playback helper
// ---------------------------------------------------------------------------

function playAudioBase64(b64Data: string, format: string = 'mp3'): void {
	try {
		const byteChars = atob(b64Data);
		const byteArray = new Uint8Array(byteChars.length);
		for (let i = 0; i < byteChars.length; i++) {
			byteArray[i] = byteChars.charCodeAt(i);
		}
		const blob = new Blob([byteArray], { type: `audio/${format}` });
		const url = URL.createObjectURL(blob);
		const audio = new Audio(url);
		audio.onended = () => URL.revokeObjectURL(url);
		audio.play().catch((err) => console.error('[audioStore] Playback failed:', err));
	} catch (err) {
		console.error('[audioStore] Failed to decode/play audio:', err);
	}
}

// ---------------------------------------------------------------------------
// WebSocket helpers
// ---------------------------------------------------------------------------

export function setLanguage(lang: 'en' | 'zh') {
	const prev = get(currentLanguage);
	if (prev === lang) return;

	currentLanguage.set(lang);

	// Completely isolate sessions: disconnect old WebSocket so the backend
	// finalizes the session report and resets conversation context.
	// When user records or speaks in the new language, a fresh WebSocket will connect.
	disconnectWebSocket();
	console.log(`[audioStore] Switched language to ${lang} and closed previous session connection.`);
}

export function setChineseLevel(level: ChineseLevel) {
	chineseLevel.set(level);
	if (ws && ws.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify({ type: 'SET_LEVEL', level }));
		console.log('[audioStore] Sent SET_LEVEL command:', level);
	}
}

function connectWebSocket(): Promise<void> {
	return new Promise((resolve, reject) => {
		if (ws && ws.readyState === WebSocket.OPEN) {
			connectionStatus.set('connected');
			return resolve();
		}

		connectionStatus.set('connecting');

		let activeLang = 'en';
		let activeLevel = 'beginner_tutor';
		currentLanguage.subscribe((val) => (activeLang = val))();
		chineseLevel.subscribe((val) => (activeLevel = val))();

		if (typeof window !== 'undefined') {
			const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
			// Since we set up a Vite proxy in vite.config.ts, we can just point to the same host
			WS_URL = `${protocol}//${window.location.host}/ws/audio?lang=${activeLang}&level=${activeLevel}`;
		}
		
		ws = new WebSocket(WS_URL);

		ws.onopen = () => {
			connectionStatus.set('connected');
			console.log('[audioStore] WebSocket connected with language:', activeLang, 'level:', activeLevel);
			if (ws && ws.readyState === WebSocket.OPEN) {
				ws.send(JSON.stringify({ type: 'SET_LANGUAGE', language: activeLang }));
				if (activeLang === 'zh') {
					ws.send(JSON.stringify({ type: 'SET_LEVEL', level: activeLevel }));
				}
			}
			resolve();
		};

		ws.onmessage = (event: MessageEvent) => {
			try {
				const data: WSMessage = {
					...JSON.parse(event.data),
					timestamp: Date.now(),
				};

				// Update connection status based on pipeline stage
				if (data.type === 'status' && data.status) {
					if (data.status === 'language_changed' && data.language) {
						currentLanguage.set(data.language as 'en' | 'zh');
					}
					if (data.status === 'level_changed' && (data as any).level) {
						chineseLevel.set((data as any).level as ChineseLevel);
					}

					const statusMap: Record<string, ConnectionStatus> = {
						transcribing: 'transcribing',
						thinking: 'thinking',
						speaking: 'speaking',
						done: 'connected',
					};
					const mapped = statusMap[data.status];
					if (mapped) connectionStatus.set(mapped);
				}

				const activeLang = get(currentLanguage);

				// Capture transcription
				if (data.type === 'transcription' && data.transcription) {
					if (activeLang === 'zh') {
						zhLatestTranscription.set(data.transcription);
					} else {
						enLatestTranscription.set(data.transcription);
					}
				}

				// Capture acoustic tone analysis (Chinese only)
				if (data.type === 'tone_analysis' && data.tone_analysis) {
					latestToneAnalysis.set(data.tone_analysis);
				}

				// Capture LLM response
				if (data.type === 'llm_response' && data.llm_text) {
					if (activeLang === 'zh') {
						zhLatestLLMResponse.set(data.llm_text);
					} else {
						enLatestLLMResponse.set(data.llm_text);
					}
				}

				// Auto-play TTS audio & record latest audio for potential download
				if (data.type === 'tts_audio' && data.audio_b64) {
					const spokenText = activeLang === 'zh' ? get(zhLatestLLMResponse) : get(enLatestLLMResponse);
					latestAudioB64.set({
						b64: data.audio_b64,
						format: data.audio_format || 'mp3',
						text: spokenText,
						language: activeLang,
					});
					playAudioBase64(data.audio_b64, data.audio_format || 'mp3');
				}

				// Log non-status messages to conversation history of the active language
				if (data.type !== 'status') {
					const targetLog = activeLang === 'zh' ? zhMessageLog : enMessageLog;
					if (data.type === 'tone_analysis') {
						if (data.tone_analysis?.tones && data.tone_analysis.tones.length > 0) {
							targetLog.update((log) => [...log, data]);
						}
					} else {
						targetLog.update((log) => [...log, data]);
					}
				}
			} catch (err) {
				console.error('[audioStore] Failed to parse WS message:', err);
			}
		};

		ws.onerror = (event) => {
			console.error('[audioStore] WebSocket error:', event);
			connectionStatus.set('error');
			reject(new Error('WebSocket connection failed'));
		};

		ws.onclose = () => {
			connectionStatus.set('disconnected');
			console.log('[audioStore] WebSocket closed');
			ws = null;
		};
	});
}

export function disconnectWebSocket() {
	if (ws) {
		ws.close();
		ws = null;
	}
	connectionStatus.set('disconnected');
}

// ---------------------------------------------------------------------------
// MediaRecorder helpers
// ---------------------------------------------------------------------------

async function startCapture(): Promise<void> {
	mediaStream = await navigator.mediaDevices.getUserMedia({
		audio: {
			channelCount: { ideal: 1 },
			sampleRate: { ideal: 16_000 },
			echoCancellation: true,
			noiseSuppression: true,
			autoGainControl: true,
		},
	});

	mediaRecorder = new MediaRecorder(mediaStream, {
		mimeType: 'audio/webm;codecs=opus',
	});

	mediaRecorder.ondataavailable = (event: BlobEvent) => {
		if (event.data.size > 0 && ws?.readyState === WebSocket.OPEN) {
			const p = event.data.arrayBuffer().then((buffer) => {
				if (ws?.readyState === WebSocket.OPEN) {
					ws.send(buffer);
				}
			});
			chunkPromises.push(p);
		}
	};

	mediaRecorder.start(CHUNK_INTERVAL_MS);
	console.log('[audioStore] MediaRecorder started');
}

function stopCapture(): Promise<void> {
	return new Promise((resolve) => {
		if (!mediaRecorder || mediaRecorder.state === 'inactive') {
			cleanupStream();
			return resolve();
		}

		mediaRecorder.onstop = async () => {
			await Promise.all(chunkPromises);
			chunkPromises = [];
			cleanupStream();
			console.log('[audioStore] MediaRecorder stopped and flushed');
			resolve();
		};

		mediaRecorder.stop();
	});
}

function cleanupStream() {
	mediaRecorder = null;
	if (mediaStream) {
		mediaStream.getTracks().forEach((track) => track.stop());
		mediaStream = null;
	}
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Start recording: connect WebSocket → start microphone capture.
 */
export async function startRecording(): Promise<void> {
	try {
		await connectWebSocket();
		await startCapture();
		isRecording.set(true);
	} catch (err) {
		console.error('[audioStore] Failed to start recording:', err);
		stopCapture();
		disconnectWebSocket();
		isRecording.set(false);
		throw err;
	}
}

/**
 * Stop recording: stop mic → send STOP → keep WS open for the full
 * ASR → LLM → TTS pipeline response.
 */
export async function stopRecording(): Promise<void> {
	await stopCapture();
	isRecording.set(false);

	const currentWs = ws;
	if (currentWs && currentWs.readyState === WebSocket.OPEN) {
		connectionStatus.set('transcribing');
		console.log('[audioStore] Sending STOP …');
		currentWs.send('STOP');

		const originalOnMessage = currentWs.onmessage;
		currentWs.onmessage = (event: MessageEvent) => {
			if (originalOnMessage) {
				originalOnMessage.call(currentWs, event);
			}
			try {
				const data = JSON.parse(event.data);
				// We no longer close the WebSocket when done.
				// It remains open for the next conversation turn!
			} catch {
				// ignore parse errors
			}
		};
	} else {
		connectionStatus.set('disconnected');
	}
}

/**
 * Toggle recording on/off.
 */
export async function toggleRecording(): Promise<void> {
	if (get(isRecording)) {
		stopRecording();
	} else {
		await startRecording();
	}
}

/**
 * Clear the message log and LLM conversation history.
 */
export function clearLog(): void {
	const activeLang = get(currentLanguage);
	if (activeLang === 'zh') {
		zhMessageLog.set([]);
		zhLatestTranscription.set('');
		zhLatestLLMResponse.set('');
		latestToneAnalysis.set(null);
	} else {
		enMessageLog.set([]);
		enLatestTranscription.set('');
		enLatestLLMResponse.set('');
	}
	latestAudioB64.set(null);

	// Also tell the backend to clear LLM history for this session
	if (ws && ws.readyState === WebSocket.OPEN) {
		ws.send('CLEAR');
	}
}

/**
 * Switch mode between interactive conversational tutor and TTS Studio.
 */
export function setAppMode(mode: AppMode): void {
	currentMode.set(mode);
}

/**
 * Call the backend REST API to synthesize high-definition audio.
 */
export async function generateTTSAudio(params: {
	text: string;
	language?: string;
	rate?: string;
	pitch?: string;
	voice?: string;
}): Promise<TTSGenerateResult> {
	const backendHost =
		typeof window !== 'undefined' && window.location.hostname
			? window.location.hostname
			: 'localhost';
	const endpoint = `http://${backendHost}:8000/api/tts/generate`;

	const response = await fetch(endpoint, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			text: params.text,
			language: params.language ?? 'zh',
			rate: params.rate ?? '+0%',
			pitch: params.pitch ?? '+0Hz',
			voice: params.voice,
		}),
	});

	if (!response.ok) {
		const err = await response.json().catch(() => ({ detail: response.statusText }));
		throw new Error(err.detail || 'Impossibile generare l\'audio');
	}

	return (await response.json()) as TTSGenerateResult;
}

