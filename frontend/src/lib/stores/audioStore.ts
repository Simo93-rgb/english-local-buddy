/**
 * Audio Store – WebSocket & MediaRecorder state management
 * =========================================================
 * Handles microphone capture via the Web Audio API (MediaRecorder)
 * and streams audio chunks over a WebSocket to the Python backend.
 *
 * Flow:
 *   1. User clicks "Start" → WebSocket connects → MediaRecorder starts
 *   2. Audio chunks (WebM/Opus, ~250 ms) are streamed as binary frames
 *   3. User clicks "Stop" → MediaRecorder stops → text "STOP" sent to backend
 *   4. Backend transcribes the accumulated audio and returns JSON
 *   5. WebSocket is closed after the response is received
 */

import { writable, derived, get } from 'svelte/store';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WSMessage {
	status: string;
	transcription?: string;
	confidence?: number;
	language?: string;
	segments?: Array<{ start: number; end: number; text: string; avg_logprob: number }>;
	gop_score?: number | null;
	message?: string;
	// Legacy mock fields (kept for backwards compatibility)
	mock_transcription?: string;
	mock_gop_score?: number;
	timestamp: number;
}

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'transcribing' | 'error';

// ---------------------------------------------------------------------------
// Stores
// ---------------------------------------------------------------------------

/** Whether the microphone is currently recording */
export const isRecording = writable<boolean>(false);

/** WebSocket connection status */
export const connectionStatus = writable<ConnectionStatus>('disconnected');

/** Log of messages received from the backend */
export const messageLog = writable<WSMessage[]>([]);

/** The latest message from the backend */
export const latestMessage = derived(messageLog, ($log) =>
	$log.length > 0 ? $log[$log.length - 1] : null
);

// ---------------------------------------------------------------------------
// Internal state (not reactive – module-level singletons)
// ---------------------------------------------------------------------------

let ws: WebSocket | null = null;
let mediaRecorder: MediaRecorder | null = null;
let mediaStream: MediaStream | null = null;

const WS_URL = 'ws://localhost:8000/ws/audio';
const CHUNK_INTERVAL_MS = 250;

// ---------------------------------------------------------------------------
// WebSocket helpers
// ---------------------------------------------------------------------------

function connectWebSocket(): Promise<void> {
	return new Promise((resolve, reject) => {
		connectionStatus.set('connecting');

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
				messageLog.update((log) => [...log, data]);

				// If we got a transcription result back, we can close the socket
				if (data.status === 'ok' || data.status === 'empty' || data.status === 'error') {
					connectionStatus.set('connected');
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

function disconnectWebSocket() {
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

	// Collect audio data and send over WebSocket at regular intervals
	mediaRecorder.ondataavailable = (event: BlobEvent) => {
		if (event.data.size > 0 && ws?.readyState === WebSocket.OPEN) {
			event.data.arrayBuffer().then((buffer) => {
				ws?.send(buffer);
			});
		}
	};

	// Request data every CHUNK_INTERVAL_MS
	mediaRecorder.start(CHUNK_INTERVAL_MS);

	console.log('[audioStore] MediaRecorder started');
}

function stopCapture() {
	if (mediaRecorder && mediaRecorder.state !== 'inactive') {
		mediaRecorder.stop();
	}
	mediaRecorder = null;

	if (mediaStream) {
		mediaStream.getTracks().forEach((track) => track.stop());
		mediaStream = null;
	}

	console.log('[audioStore] MediaRecorder stopped');
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
 * Stop recording: stop microphone → send STOP command → wait for
 * the transcription result, then close the WebSocket.
 */
export function stopRecording(): void {
	// 1. Stop the microphone immediately
	stopCapture();
	isRecording.set(false);

	// 2. Tell the backend to transcribe the buffered audio
	const currentWs = ws;
	if (currentWs && currentWs.readyState === WebSocket.OPEN) {
		connectionStatus.set('transcribing');
		console.log('[audioStore] Sending STOP command …');
		currentWs.send('STOP');

		// 3. Give the backend time to respond, then close
		//    (the onmessage handler will log the result)
		//    Close after a generous timeout to handle slow transcriptions
		const closeTimeout = setTimeout(() => {
			disconnectWebSocket();
		}, 30_000); // 30 s max wait

		// If we receive a message, close sooner
		const originalOnMessage = currentWs.onmessage;
		currentWs.onmessage = (event: MessageEvent) => {
			// Process the message with the original handler
			if (originalOnMessage) {
				originalOnMessage.call(currentWs, event);
			}
			// Close after receiving the transcription result
			clearTimeout(closeTimeout);
			setTimeout(() => disconnectWebSocket(), 500);
		};
	} else {
		disconnectWebSocket();
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
 * Clear the message log.
 */
export function clearLog(): void {
	messageLog.set([]);
}
