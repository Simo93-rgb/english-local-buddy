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
		currentLanguage,
		setLanguage,
		chineseLevel,
		setChineseLevel,
		currentMode,
		setAppMode,
		latestToneAnalysis,
		latestAudioB64,
		saveAudioFile,
		type ChineseLevel,
	} from '$lib/stores/audioStore';
	import TTSStudio from '$lib/components/TTSStudio.svelte';

	let error = $state<string | null>(null);
	let reportMessage = $state<string | null>(null);
	let downloadingAudio = $state<boolean>(false);

	function handleTutorSelect(value: string) {
		if (value === 'tts_studio') {
			setAppMode('tts_studio');
		} else {
			setAppMode('tutor');
			setChineseLevel(value as ChineseLevel);
		}
	}

	async function handleDownloadResponseAudio() {
		const audioData = $latestAudioB64;
		if (!audioData || !audioData.b64) return;
		downloadingAudio = true;
		try {
			const cleanText = (audioData.text || 'buddy_response')
				.replace(/[^\w\u4e00-\u9fff-]+/g, '_')
				.slice(0, 25)
				.replace(/^_+|_+$/g, '') || 'audio_risposta';
			const filename = `${cleanText}_${audioData.language}.mp3`;
			const res = await saveAudioFile({
				b64Data: audioData.b64,
				filename,
				format: audioData.format || 'mp3',
			});
			if (res.success) {
				reportMessage = `Audio scaricato con successo in: ${res.path || filename}`;
				setTimeout(() => {
					reportMessage = null;
				}, 8000);
			} else if (res.message !== 'Salvataggio annullato.') {
				error = res.message;
			}
		} finally {
			downloadingAudio = false;
		}
	}

	async function handleToggle() {
		error = null;
		reportMessage = null;
		try {
			await toggleRecording();
		} catch (err: any) {
			const msg = err instanceof Error ? err.message : String(err);
			if (
				msg.includes('not allowed') ||
				msg.includes('denied') ||
				msg.includes('Permission') ||
				err?.name === 'NotAllowedError'
			) {
				error =
					'Accesso al microfono non consentito dal browser o dal sistema. ' +
					'Assicurati di accedere tramite http://localhost:1420 (e non tramite IP di rete) ' +
					'e di aver consentito il permesso per il microfono nelle impostazioni del browser o del sistema.';
			} else {
				error = msg || 'Impossibile avviare la registrazione.';
			}
		}
	}

	function handleDisconnect() {
		disconnectWebSocket();
		const reportName = $currentLanguage === 'zh' ? 'user_history/user_chinese_report.md' : 'user_history/user_report.md';
		reportMessage = `Session ended. Your progress report has been updated in '${reportName}'.`;
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
	<title>{$currentLanguage === 'zh' ? 'Chinese Buddy – Tutor Cinese Mandarino' : 'English Buddy – Pronunciation Trainer'}</title>
	<meta name="description" content="Local AI-powered language training app" />
</svelte:head>

<main class="min-h-screen bg-gray-950 text-gray-100 flex flex-col items-center px-4 py-10">
	<!-- Header -->
	<header class="text-center mb-6">
		<h1 class="text-4xl font-bold tracking-tight bg-gradient-to-r {$currentLanguage === 'zh' ? 'from-rose-400 via-amber-300 to-red-400' : 'from-indigo-400 to-cyan-400'} bg-clip-text text-transparent">
			{$currentLanguage === 'zh' ? 'Chinese Buddy' : 'English Buddy'}
		</h1>
		<p class="mt-2 text-gray-400 text-sm">
			{#if $currentLanguage === 'zh'}
				{#if $currentMode === 'tts_studio'}
					🎙️ Generatore Audio HD: Sintesi Vocale e Pronuncia Naturale di Pinyin e Hanzi
				{:else if $chineseLevel === 'beginner_tutor'}
					🎓 Tutor Bilingue Principianti: Fonetica, Vocali, Consonanti, Toni & Cultura
				{:else if $chineseLevel === 'intermediate'}
					🗣️ Pratica Guidata Bilingue: Dialoghi Quotidiani & Grammatica
				{:else}
					🚀 Conversational Buddy: Dialogo Fluente in Cinese Mandarino
				{/if}
			{:else}
				{#if $currentMode === 'tts_studio'}
					🎙️ Generatore Audio HD: Sintesi Vocale e Pronuncia Naturale in Inglese Americano
				{:else}
					🗣️ Conversational Partner: Pratica Vocale Naturale & Pronuncia Inglese
				{/if}
			{/if}
		</p>
	</header>

	<!-- Language Selector -->
	<div class="mb-4 flex items-center bg-gray-900/90 p-1.5 rounded-2xl border border-gray-800 shadow-inner">
		<button
			onclick={() => { setLanguage('en'); setAppMode('tutor'); }}
			class="px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 {$currentLanguage === 'en' ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30' : 'text-gray-400 hover:text-gray-200'}"
		>
			<span class="text-sm">🇬🇧</span>
			<span>English Buddy</span>
		</button>
		<button
			onclick={() => { setLanguage('zh'); setAppMode('tutor'); }}
			class="px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 {$currentLanguage === 'zh' ? 'bg-rose-600 text-white shadow-md shadow-rose-600/30' : 'text-gray-400 hover:text-gray-200'}"
		>
			<span class="text-sm">🇨🇳</span>
			<span>Chinese Buddy</span>
		</button>
	</div>

	<!-- English Tutor & Tool Selector -->
	{#if $currentLanguage === 'en'}
		<div class="mb-6 w-full max-w-xl flex flex-col items-center gap-2.5">
			<!-- Menu a tendina principale -->
			<div class="w-full flex items-center justify-between gap-3 bg-gray-900/90 p-2.5 px-4 rounded-2xl border border-indigo-900/40 shadow-lg">
				<label for="en-tutor-mode-select" class="text-xs font-semibold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5 shrink-0">
					<span>Tutor / Strumento:</span>
				</label>
				<select
					id="en-tutor-mode-select"
					value={$currentMode}
					onchange={(e) => setAppMode((e.target as HTMLSelectElement).value as any)}
					class="w-full bg-gray-950 text-gray-100 text-xs sm:text-sm font-medium py-2 px-3 rounded-xl border border-indigo-900/40 focus:border-indigo-500 focus:outline-none cursor-pointer"
				>
					<optgroup label="Tutor Interattivo (Conversazione Vocale)">
						<option value="tutor">🗣️ Conversational Partner (Pratica Vocale Naturale)</option>
					</optgroup>
					<optgroup label="Strumenti Audio AI">
						<option value="tts_studio">🎙️ Generatore Audio HD (Pronuncia Inglese & TTS)</option>
					</optgroup>
				</select>
			</div>

			<!-- Quick tabs selector -->
			<div class="flex flex-wrap items-center justify-center gap-1.5 bg-gray-900/70 p-1.5 rounded-2xl border border-indigo-900/30 shadow-inner w-full">
				<button
					onclick={() => setAppMode('tutor')}
					class="px-4 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 {$currentMode === 'tutor' ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-400 hover:text-indigo-200'}"
				>
					<span>🗣️ Conversational Partner</span>
				</button>
				<button
					onclick={() => setAppMode('tts_studio')}
					class="px-4 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 {$currentMode === 'tts_studio' ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30' : 'text-gray-400 hover:text-blue-300'}"
				>
					<span>🎙️ Generatore Audio HD</span>
				</button>
			</div>
		</div>
	{/if}

	<!-- Chinese Tutor & Tool Selector (Menu a tendina + quick tabs) -->
	{#if $currentLanguage === 'zh'}
		<div class="mb-6 w-full max-w-xl flex flex-col items-center gap-2.5">
			<!-- Menu a tendina principale -->
			<div class="w-full flex items-center justify-between gap-3 bg-gray-900/90 p-2.5 px-4 rounded-2xl border border-rose-900/40 shadow-lg">
				<label for="tutor-mode-select" class="text-xs font-semibold text-rose-300 uppercase tracking-wider flex items-center gap-1.5 shrink-0">
					<span>Tutor / Strumento:</span>
				</label>
				<select
					id="tutor-mode-select"
					value={$currentMode === 'tts_studio' ? 'tts_studio' : $chineseLevel}
					onchange={(e) => handleTutorSelect((e.target as HTMLSelectElement).value)}
					class="w-full bg-gray-950 text-gray-100 text-xs sm:text-sm font-medium py-2 px-3 rounded-xl border border-rose-900/40 focus:border-rose-500 focus:outline-none cursor-pointer"
				>
					<optgroup label="Tutor Interattivi (Conversazione Vocale)">
						<option value="beginner_tutor">🎓 Principiante (Fonetica, Toni & Cultura)</option>
						<option value="intermediate">🗣️ Intermedio (Dialoghi & Pratica Guidata)</option>
						<option value="advanced_buddy">🚀 Avanzato (Conversazione Libera)</option>
					</optgroup>
					<optgroup label="Strumenti Audio AI">
						<option value="tts_studio">🎙️ Generatore Audio HD (Pinyin & Hanzi)</option>
					</optgroup>
				</select>
			</div>

			<!-- Quick tabs selector -->
			<div class="flex flex-wrap items-center justify-center gap-1.5 bg-gray-900/70 p-1.5 rounded-2xl border border-rose-900/30 shadow-inner w-full">
				<button
					onclick={() => handleTutorSelect('beginner_tutor')}
					class="px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 {$currentMode === 'tutor' && $chineseLevel === 'beginner_tutor' ? 'bg-rose-600 text-white shadow-sm' : 'text-gray-400 hover:text-rose-200'}"
				>
					<span>🎓 Principiante</span>
				</button>
				<button
					onclick={() => handleTutorSelect('intermediate')}
					class="px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 {$currentMode === 'tutor' && $chineseLevel === 'intermediate' ? 'bg-rose-600 text-white shadow-sm' : 'text-gray-400 hover:text-rose-200'}"
				>
					<span>🗣️ Intermedio</span>
				</button>
				<button
					onclick={() => handleTutorSelect('advanced_buddy')}
					class="px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 {$currentMode === 'tutor' && $chineseLevel === 'advanced_buddy' ? 'bg-rose-600 text-white shadow-sm' : 'text-gray-400 hover:text-rose-200'}"
				>
					<span>🚀 Avanzato</span>
				</button>
				<button
					onclick={() => handleTutorSelect('tts_studio')}
					class="px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 {$currentMode === 'tts_studio' ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30' : 'text-gray-400 hover:text-blue-300'}"
				>
					<span>🎙️ Generatore Audio HD</span>
				</button>
			</div>
		</div>
	{/if}

	{#if $currentMode === 'tts_studio'}
		<TTSStudio />
	{:else}
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
					: $currentLanguage === 'zh'
						? 'bg-rose-600 shadow-lg shadow-rose-600/40 hover:bg-rose-500'
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
		{#if $isRecording}
			{$currentLanguage === 'zh' ? 'Registrazione in corso… clicca per fermare' : 'Recording… click to stop'}
		{:else if $connectionStatus === 'transcribing'}
			{$currentLanguage === 'zh' ? 'Trascrizione audio in corso…' : 'Transcribing your audio…'}
		{:else if $connectionStatus === 'thinking'}
			{$currentLanguage === 'zh' ? 'Il tutor sta generando la risposta…' : 'Generating response…'}
		{:else if $connectionStatus === 'speaking'}
			{$currentLanguage === 'zh' ? '🔊 Riproduzione pronuncia e spiegazione…' : '🔊 Playing response…'}
		{:else}
			{$currentLanguage === 'zh' ? 'Clicca per parlare (parla in cinese o chiedi spiegazioni in italiano)' : 'Click to start recording'}
		{/if}
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
					<span class="text-xs font-semibold {$currentLanguage === 'zh' ? 'text-rose-400' : 'text-indigo-400'} uppercase tracking-wider">
						{$currentLanguage === 'zh' ? 'Hai detto' : 'You said'}
					</span>
				</div>
				<p class="text-lg text-white">{$latestTranscription}</p>
			</div>
		{/if}

		<!-- Bot's response -->
		{#if $latestLLMResponse}
			<div class="rounded-2xl border {$currentLanguage === 'zh' ? 'border-rose-900/50 bg-rose-950/20' : 'border-cyan-900/50 bg-cyan-950/30'} backdrop-blur p-5">
				<div class="flex items-center justify-between gap-2 mb-2">
					<span class="text-xs font-semibold {$currentLanguage === 'zh' ? 'text-rose-300' : 'text-cyan-400'} uppercase tracking-wider">
						{$currentLanguage === 'zh' ? '🇨🇳 Buddy (Tutor Cinese)' : '🤖 Buddy'}
					</span>

					{#if $latestAudioB64 && $latestAudioB64.b64}
						<button
							onclick={handleDownloadResponseAudio}
							disabled={downloadingAudio}
							class="text-xs px-2.5 py-1 rounded-lg bg-gray-900/80 hover:bg-gray-800 text-gray-300 hover:text-white border border-gray-700/60 transition-all flex items-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-50"
							title="Scarica la risposta vocale in MP3 sul tuo computer"
						>
							<svg class="w-3.5 h-3.5 {$currentLanguage === 'zh' ? 'text-rose-400' : 'text-cyan-400'}" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
							</svg>
							<span>{downloadingAudio ? 'Salvataggio…' : 'Scarica MP3'}</span>
						</button>
					{/if}
				</div>
				<p class="text-lg text-gray-100">{$latestLLMResponse}</p>
			</div>
		{/if}

		<!-- Acoustic Tone Assessment Card (shown in Chinese mode when tones are detected) -->
		{#if $currentLanguage === 'zh' && $latestToneAnalysis && $latestToneAnalysis.tones && $latestToneAnalysis.tones.length > 0}
			<div class="rounded-2xl border border-amber-900/40 bg-amber-950/20 backdrop-blur p-5 space-y-3">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<span class="text-sm">🎯</span>
						<span class="text-xs font-semibold text-amber-300 uppercase tracking-wider">
							Analisi Acustica della Pronuncia & Toni (F0)
						</span>
					</div>
					<span class="text-xs font-bold px-2.5 py-0.5 rounded-full {$latestToneAnalysis.overall_accuracy >= 80 ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50' : 'bg-amber-900/60 text-amber-300 border border-amber-700/50'}">
						{$latestToneAnalysis.overall_accuracy}% Corretto
					</span>
				</div>

				<div class="grid grid-cols-1 gap-2.5 pt-1">
					{#each $latestToneAnalysis.tones as toneItem}
						<div class="p-3 rounded-xl border {toneItem.is_correct ? 'border-emerald-900/40 bg-emerald-950/20' : 'border-rose-900/40 bg-rose-950/20'} flex flex-col gap-1">
							<div class="flex items-center justify-between">
								<div class="flex items-center gap-2">
									<span class="text-base font-bold text-white tracking-wide">{toneItem.syllable}</span>
									<span class="text-xs px-2 py-0.5 rounded-md {toneItem.is_correct ? 'bg-emerald-900/50 text-emerald-200' : 'bg-rose-900/50 text-rose-200'} font-mono">
										Atteso: {toneItem.expected_tone}° tono | Rilevato: {toneItem.detected_tone > 0 ? toneItem.detected_tone + '° tono' : 'non rilevato'}
									</span>
								</div>
								<span>{toneItem.is_correct ? '✅' : '⚠️'}</span>
							</div>
							<p class="text-xs text-gray-300 mt-0.5">{toneItem.feedback}</p>
						</div>
					{/each}
				</div>
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
								{:else if msg.type === 'tone_analysis' && msg.tone_analysis}
									<span class="text-amber-300 font-medium">🎯 Toni (F0):</span>
									<span class="text-gray-300 ml-1">{msg.tone_analysis.summary}</span>
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
	{/if}
</main>
