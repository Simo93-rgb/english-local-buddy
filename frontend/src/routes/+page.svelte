<script lang="ts">
	import {
		isRecording,
		connectionStatus,
		messageLog,
		latestTranscription,
		latestLLMResponse,
		toggleRecording,
		clearLog,
		disconnectWebSocket,
	} from '$lib/stores/audioStore';

	let error = $state<string | null>(null);
	let reportMessage = $state<string | null>(null);

	async function handleToggle() {
		error = null;
		reportMessage = null;
		try {
			await toggleRecording();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to start recording';
		}
	}

	function handleDisconnect() {
		disconnectWebSocket();
		reportMessage = "Session ended. Your progress report has been updated in 'user_history/user_report.md'.";
		setTimeout(() => {
			reportMessage = null;
		}, 10000);
	}

	function formatTime(timestamp: number): string {
		return new Date(timestamp).toLocaleTimeString('en-GB', {
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit',
		});
	}

	const statusLabels: Record<string, string> = {
		disconnected: 'Disconnected',
		connecting: 'Connecting…',
		connected: 'Connected',
		transcribing: 'Transcribing…',
		thinking: 'Thinking…',
		speaking: 'Speaking…',
		error: 'Error',
	};

	const statusColors: Record<string, string> = {
		disconnected: 'bg-gray-800 text-gray-400',
		connecting: 'bg-amber-900/50 text-amber-300',
		connected: 'bg-emerald-900/50 text-emerald-300',
		transcribing: 'bg-violet-900/50 text-violet-300',
		thinking: 'bg-blue-900/50 text-blue-300',
		speaking: 'bg-cyan-900/50 text-cyan-300',
		error: 'bg-red-900/50 text-red-300',
	};

	const dotColors: Record<string, string> = {
		disconnected: 'bg-gray-500',
		connecting: 'bg-amber-400 animate-pulse',
		connected: 'bg-emerald-400',
		transcribing: 'bg-violet-400 animate-pulse',
		thinking: 'bg-blue-400 animate-pulse',
		speaking: 'bg-cyan-400 animate-pulse',
		error: 'bg-red-400',
	};
</script>

<svelte:head>
	<title>English Buddy – Pronunciation Trainer</title>
	<meta name="description" content="Local AI-powered English pronunciation training app" />
</svelte:head>

<main class="min-h-screen bg-gray-950 text-gray-100 flex flex-col items-center px-4 py-10">
	<!-- Header -->
	<header class="text-center mb-10">
		<h1 class="text-4xl font-bold tracking-tight bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
			English Buddy
		</h1>
		<p class="mt-2 text-gray-400 text-sm">Local Pronunciation Trainer</p>
	</header>

	<!-- Connection status badge and controls -->
	<div class="mb-6 flex items-center gap-3">
		<span class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium {statusColors[$connectionStatus] ?? 'bg-gray-800 text-gray-400'}">
			<span class="h-2 w-2 rounded-full {dotColors[$connectionStatus] ?? 'bg-gray-500'}"></span>
			{statusLabels[$connectionStatus] ?? $connectionStatus}
		</span>

		{#if $connectionStatus !== 'disconnected' && $connectionStatus !== 'error'}
			<button
				id="disconnect-button"
				onclick={handleDisconnect}
				class="text-xs px-3 py-1 bg-red-950/40 text-red-300 border border-red-900/50 hover:bg-red-900/30 transition-colors rounded-full cursor-pointer"
			>
				End Session
			</button>
		{/if}
	</div>

	<!-- Record button -->
	<button
		id="record-button"
		onclick={handleToggle}
		class="relative group mb-8 cursor-pointer"
	>
		{#if $isRecording}
			<span class="absolute inset-0 rounded-full bg-red-500/20 animate-ping"></span>
		{/if}

		<span
			class="relative flex h-20 w-20 items-center justify-center rounded-full transition-all duration-300
				{$isRecording
					? 'bg-red-600 shadow-lg shadow-red-600/40 hover:bg-red-500'
					: 'bg-indigo-600 shadow-lg shadow-indigo-600/40 hover:bg-indigo-500'}"
		>
			{#if $isRecording}
				<svg class="h-8 w-8 text-white" fill="currentColor" viewBox="0 0 24 24">
					<rect x="6" y="6" width="12" height="12" rx="2" />
				</svg>
			{:else}
				<svg class="h-8 w-8 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3Z" />
					<path stroke-linecap="round" stroke-linejoin="round" d="M19 10v2a7 7 0 0 1-14 0v-2" />
					<line x1="12" y1="19" x2="12" y2="23" />
					<line x1="8" y1="23" x2="16" y2="23" />
				</svg>
			{/if}
		</span>
	</button>

	<p class="mb-8 text-sm text-gray-500">
		{$isRecording
			? 'Recording… click to stop'
			: $connectionStatus === 'transcribing'
				? 'Transcribing your audio…'
				: $connectionStatus === 'thinking'
					? 'Generating response…'
					: $connectionStatus === 'speaking'
						? '🔊 Playing response…'
						: 'Click to start recording'}
	</p>

	<!-- Error banner -->
	{#if error}
		<div class="mb-6 w-full max-w-xl rounded-lg border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-300">
			⚠️ {error}
		</div>
	{/if}

	<!-- Success banner -->
	{#if reportMessage}
		<div class="mb-6 w-full max-w-xl rounded-lg border border-emerald-800 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-300">
			✅ {reportMessage}
		</div>
	{/if}

	<!-- Conversation cards -->
	<div class="w-full max-w-xl space-y-4 mb-8">
		<!-- User's transcription -->
		{#if $latestTranscription}
			<div class="rounded-2xl border border-gray-800 bg-gray-900/60 backdrop-blur p-5">
				<div class="flex items-center gap-2 mb-2">
					<span class="text-xs font-semibold text-indigo-400 uppercase tracking-wider">You said</span>
				</div>
				<p class="text-lg text-white">{$latestTranscription}</p>
			</div>
		{/if}

		<!-- Bot's response -->
		{#if $latestLLMResponse}
			<div class="rounded-2xl border border-cyan-900/50 bg-cyan-950/30 backdrop-blur p-5">
				<div class="flex items-center gap-2 mb-2">
					<span class="text-xs font-semibold text-cyan-400 uppercase tracking-wider">🤖 Buddy</span>
				</div>
				<p class="text-lg text-gray-100">{$latestLLMResponse}</p>
			</div>
		{/if}
	</div>

	<!-- Message log -->
	<section class="w-full max-w-xl">
		<div class="flex items-center justify-between mb-3">
			<h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider">Conversation Log</h2>
			{#if $messageLog.length > 0}
				<button
					id="clear-log-button"
					onclick={clearLog}
					class="text-xs text-gray-500 hover:text-gray-300 transition-colors cursor-pointer"
				>
					Clear All
				</button>
			{/if}
		</div>

		<div
			id="message-log"
			class="rounded-2xl border border-gray-800 bg-gray-900/40 backdrop-blur max-h-80 overflow-y-auto"
		>
			{#if $messageLog.length === 0}
				<p class="px-4 py-8 text-center text-sm text-gray-600">
					No messages yet. Start recording to begin a conversation.
				</p>
			{:else}
				<ul class="divide-y divide-gray-800/60">
					{#each $messageLog as msg, i (msg.timestamp + '-' + i)}
						<li class="flex items-start gap-3 px-4 py-3 text-sm hover:bg-gray-800/30 transition-colors">
							<span class="shrink-0 text-xs font-mono text-gray-600 mt-0.5">
								{formatTime(msg.timestamp)}
							</span>
							<div class="min-w-0 flex-1">
								{#if msg.type === 'transcription'}
									<span class="text-indigo-300 font-medium">You:</span>
									<span class="text-gray-300 ml-1">{msg.transcription}</span>
								{:else if msg.type === 'llm_response'}
									<span class="text-cyan-300 font-medium">Buddy:</span>
									<span class="text-gray-300 ml-1">{msg.llm_text}</span>
								{:else if msg.type === 'tts_audio'}
									<span class="text-gray-500 italic">🔊 Audio played</span>
								{:else if msg.type === 'error'}
									<span class="text-red-400">⚠️ {msg.message}</span>
								{:else}
									<span class="text-gray-500">{msg.status}</span>
								{/if}
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</section>
</main>
