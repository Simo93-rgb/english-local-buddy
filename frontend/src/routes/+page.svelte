<script lang="ts">
	import {
		isRecording,
		connectionStatus,
		messageLog,
		latestMessage,
		toggleRecording,
		clearLog,
	} from '$lib/stores/audioStore';

	let error = $state<string | null>(null);

	async function handleToggle() {
		error = null;
		try {
			await toggleRecording();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to start recording';
		}
	}

	function formatTime(timestamp: number): string {
		return new Date(timestamp).toLocaleTimeString('en-GB', {
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit',
			fractionalSecondDigits: 3,
		});
	}
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

	<!-- Connection status badge -->
	<div class="mb-6">
		<span
			class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium
				{$connectionStatus === 'connected'
					? 'bg-emerald-900/50 text-emerald-300'
					: $connectionStatus === 'connecting'
						? 'bg-amber-900/50 text-amber-300'
						: $connectionStatus === 'transcribing'
							? 'bg-violet-900/50 text-violet-300'
							: $connectionStatus === 'error'
								? 'bg-red-900/50 text-red-300'
								: 'bg-gray-800 text-gray-400'}"
		>
			<span
				class="h-2 w-2 rounded-full
					{$connectionStatus === 'connected'
						? 'bg-emerald-400 animate-pulse'
						: $connectionStatus === 'connecting'
							? 'bg-amber-400 animate-pulse'
							: $connectionStatus === 'transcribing'
								? 'bg-violet-400 animate-pulse'
								: $connectionStatus === 'error'
									? 'bg-red-400'
									: 'bg-gray-500'}"
			></span>
			{$connectionStatus}
		</span>
	</div>

	<!-- Record button -->
	<button
		id="record-button"
		onclick={handleToggle}
		class="relative group mb-8 cursor-pointer"
	>
		<!-- Pulsing ring when recording -->
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
				<!-- Stop icon -->
				<svg class="h-8 w-8 text-white" fill="currentColor" viewBox="0 0 24 24">
					<rect x="6" y="6" width="12" height="12" rx="2" />
				</svg>
			{:else}
				<!-- Mic icon -->
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
				? 'Transcribing audio…'
				: 'Click to start recording'}
	</p>

	<!-- Error banner -->
	{#if error}
		<div class="mb-6 w-full max-w-xl rounded-lg border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-300">
			⚠️ {error}
		</div>
	{/if}

	<!-- Latest result card -->
	{#if $latestMessage}
		<div class="mb-8 w-full max-w-xl rounded-2xl border border-gray-800 bg-gray-900/60 backdrop-blur p-6">
			<h2 class="text-lg font-semibold text-gray-200 mb-4">Latest Result</h2>
			<div class="grid grid-cols-1 gap-4">
				<div>
					<p class="text-xs text-gray-500 uppercase tracking-wider">Transcription</p>
					<p class="mt-1 text-xl font-medium text-white">
						{$latestMessage.transcription || $latestMessage.mock_transcription || '—'}
					</p>
				</div>
				<div class="grid grid-cols-2 gap-4">
					<div>
						<p class="text-xs text-gray-500 uppercase tracking-wider">Confidence</p>
						<p class="mt-1 text-lg font-semibold text-cyan-400">
							{$latestMessage.confidence != null
								? (($latestMessage.confidence ?? 0) * 100).toFixed(1) + '%'
								: '—'}
						</p>
					</div>
					<div>
						<p class="text-xs text-gray-500 uppercase tracking-wider">GOP Score</p>
						<p class="mt-1 text-lg font-semibold text-gray-500">
							{$latestMessage.gop_score ?? 'N/A'}
						</p>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Message log -->
	<section class="w-full max-w-xl">
		<div class="flex items-center justify-between mb-3">
			<h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider">Message Log</h2>
			{#if $messageLog.length > 0}
				<button
					id="clear-log-button"
					onclick={clearLog}
					class="text-xs text-gray-500 hover:text-gray-300 transition-colors cursor-pointer"
				>
					Clear
				</button>
			{/if}
		</div>

		<div
			id="message-log"
			class="rounded-2xl border border-gray-800 bg-gray-900/40 backdrop-blur max-h-80 overflow-y-auto"
		>
			{#if $messageLog.length === 0}
				<p class="px-4 py-8 text-center text-sm text-gray-600">
					No messages yet. Start recording to see results.
				</p>
			{:else}
				<ul class="divide-y divide-gray-800/60">
					{#each $messageLog as msg, i (msg.timestamp + '-' + i)}
						<li class="flex items-center gap-4 px-4 py-3 text-sm hover:bg-gray-800/30 transition-colors">
							<span class="shrink-0 text-xs font-mono text-gray-600">
								{formatTime(msg.timestamp)}
							</span>
							<span class="text-gray-300 truncate">
								"{msg.transcription || msg.mock_transcription || '…'}"
							</span>
							{#if msg.confidence != null}
								<span class="ml-auto shrink-0 rounded-full bg-cyan-900/40 px-2 py-0.5 text-xs font-semibold text-cyan-300">
									{((msg.confidence ?? 0) * 100).toFixed(0)}%
								</span>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</section>
</main>
