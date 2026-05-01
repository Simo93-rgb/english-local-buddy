/**
 * Audio Store – WebSocket & MediaRecorder state management
 * =========================================================
 * Handles microphone capture via the Web Audio API (MediaRecorder)
 * and streams audio chunks over a WebSocket to the Python backend.
 */

import { writable, derived, get } from 'svelte/store';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WSMessage {
	status: string;
	mock_transcription?: string;
	mock_gop_score?: number;
	timestamp: number;
}

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

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
let chunkInterval: ReturnType<typeof setInterval> | null = null;

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
 * Stop recording: stop microphone → close WebSocket.
 */
export function stopRecording(): void {
	stopCapture();
	disconnectWebSocket();
	isRecording.set(false);
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
