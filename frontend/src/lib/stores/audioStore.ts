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

export interface WSMessage {
	type?: string;
	status: string;
	transcription?: string;
	confidence?: number;
	language?: string;
	segments?: Array<{ start: number; end: number; text: string; avg_logprob: number }>;
	gop_score?: number | null;
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

// ---------------------------------------------------------------------------
// Stores
// ---------------------------------------------------------------------------

/** Whether the microphone is currently recording */
export const isRecording = writable<boolean>(false);

/** WebSocket connection status */
export const connectionStatus = writable<ConnectionStatus>('disconnected');

/** Log of messages received from the backend */
export const messageLog = writable<WSMessage[]>([]);

/** The latest transcription text */
export const latestTranscription = writable<string>('');

/** The latest LLM response text */
export const latestLLMResponse = writable<string>('');

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

function connectWebSocket(): Promise<void> {
	return new Promise((resolve, reject) => {
		if (ws && ws.readyState === WebSocket.OPEN) {
			connectionStatus.set('connected');
			return resolve();
		}

		connectionStatus.set('connecting');

		if (typeof window !== 'undefined') {
			const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
			// Since we set up a Vite proxy in vite.config.ts, we can just point to the same host
			WS_URL = `${protocol}//${window.location.host}/ws/audio`;
		}
		
		ws = new WebSocket(WS_URL);

		ws.onopen = () => {
			connectionStatus.set('connected');
			console.log('[audioStore] WebSocket connected');
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
					const statusMap: Record<string, ConnectionStatus> = {
						transcribing: 'transcribing',
						thinking: 'thinking',
						speaking: 'speaking',
						done: 'connected',
					};
					const mapped = statusMap[data.status];
					if (mapped) connectionStatus.set(mapped);
				}

				// Capture transcription
				if (data.type === 'transcription' && data.transcription) {
					latestTranscription.set(data.transcription);
				}

				// Capture LLM response
				if (data.type === 'llm_response' && data.llm_text) {
					latestLLMResponse.set(data.llm_text);
				}

				// Auto-play TTS audio
				if (data.type === 'tts_audio' && data.audio_b64) {
					playAudioBase64(data.audio_b64, data.audio_format || 'mp3');
				}

				// Log all non-status messages
				if (data.type !== 'status') {
					messageLog.update((log) => [...log, data]);
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
			channelCount: 1,
			sampleRate: 16_000,
			echoCancellation: true,
			noiseSuppression: true,
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
	messageLog.set([]);
	latestTranscription.set('');
	latestLLMResponse.set('');

	// Also tell the backend to clear LLM history
	if (ws && ws.readyState === WebSocket.OPEN) {
		ws.send('CLEAR');
	}
}
