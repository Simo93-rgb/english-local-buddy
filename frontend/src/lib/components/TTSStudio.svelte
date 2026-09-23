<script lang="ts">
	import { generateTTSAudio, type TTSGenerateResult } from '$lib/stores/audioStore';
	import { save } from '@tauri-apps/plugin-dialog';
	import { writeFile } from '@tauri-apps/plugin-fs';

	// Component state
	let inputText = $state<string>('');
	let selectedSpeed = $state<string>('1.0');
	let selectedPitch = $state<string>('0');
	let isGenerating = $state<boolean>(false);
	let errorMessage = $state<string | null>(null);
	let generatedResult = $state<TTSGenerateResult | null>(null);
	let savedNotification = $state<{ type: 'success' | 'error'; message: string; path?: string } | null>(null);

	// Audio player state
	let audioElement: HTMLAudioElement | null = null;
	let isPlaying = $state<boolean>(false);
	let currentTime = $state<number>(0);
	let duration = $state<number>(0);
	let audioBlobUrl = $state<string | null>(null);

	// Live counters
	let charCount = $derived(inputText.length);
	let wordCount = $derived(
		inputText.trim() === ''
			? 0
			: inputText.trim().split(/\s+/).filter(Boolean).length
	);

	// Quick pinyin diacritic vowels for easy typing
	const pinyinVowels = [
		['ā', 'á', 'ǎ', 'à'],
		['ē', 'é', 'ě', 'è'],
		['ī', 'í', 'ǐ', 'ì'],
		['ō', 'ó', 'ǒ', 'ò'],
		['ū', 'ú', 'ǔ', 'ù'],
		['ǖ', 'ǘ', 'ǚ', 'ǜ'],
	];

	// Presets
	const samplePhrases = [
		{ label: 'Saluto base', text: 'nǐ hǎo, huānyíng nǐ!' },
		{ label: '4 Toni (mā má mǎ mà)', text: 'mā má mǎ mà' },
		{ label: 'Come ti chiami?', text: 'nǐ jiào shénme míngzi?' },
		{ label: 'Hanzi (Piacere di conoscerti)', text: '你好，很高兴认识你！' },
		{ label: 'Hanzi (Studio il cinese)', text: '我正在努力学中文。' },
	];

	function insertChar(char: string) {
		inputText += char;
	}

	function applySample(sample: string) {
		inputText = sample;
		errorMessage = null;
	}

	function clearInput() {
		inputText = '';
		errorMessage = null;
		generatedResult = null;
		if (audioBlobUrl) {
			URL.revokeObjectURL(audioBlobUrl);
			audioBlobUrl = null;
		}
	}

	function getRateParam(speed: string): string {
		switch (speed) {
			case '0.75':
				return '-25%';
			case '0.85':
				return '-15%';
			case '1.0':
				return '+0%';
			case '1.25':
				return '+25%';
			case '1.5':
				return '+50%';
			default:
				return '+0%';
		}
	}

	function getPitchParam(pitch: string): string {
		switch (pitch) {
			case '-1':
				return '-30Hz';
			case '0':
				return '+0Hz';
			case '+1':
				return '+30Hz';
			default:
				return '+0Hz';
		}
	}

	async function handleGenerate() {
		if (!inputText.trim()) {
			errorMessage = 'Inserisci del testo in Pinyin o caratteri cinesi prima di generare.';
			return;
		}

		errorMessage = null;
		savedNotification = null;
		isGenerating = true;

		try {
			const res = await generateTTSAudio({
				text: inputText.trim(),
				language: 'zh',
				rate: getRateParam(selectedSpeed),
				pitch: getPitchParam(selectedPitch),
			});

			generatedResult = res;

			// Prepare audio blob URL for player and download
			const byteChars = atob(res.audio_b64);
			const byteArray = new Uint8Array(byteChars.length);
			for (let i = 0; i < byteChars.length; i++) {
				byteArray[i] = byteChars.charCodeAt(i);
			}

			if (audioBlobUrl) {
				URL.revokeObjectURL(audioBlobUrl);
			}

			const blob = new Blob([byteArray], { type: 'audio/mp3' });
			audioBlobUrl = URL.createObjectURL(blob);

			// Automatically start playback
			if (audioElement) {
				audioElement.src = audioBlobUrl;
				audioElement.currentTime = 0;
				audioElement.play().catch((err) => console.log('Auto-play blocked or failed:', err));
				isPlaying = true;
			}
		} catch (err: any) {
			errorMessage = err?.message || 'Errore durante la generazione dell\'audio.';
		} finally {
			isGenerating = false;
		}
	}

	function togglePlay() {
		if (!audioElement || !audioBlobUrl) return;

		if (isPlaying) {
			audioElement.pause();
			isPlaying = false;
		} else {
			audioElement.play().catch((err) => console.error('Play error:', err));
			isPlaying = true;
		}
	}

	function handleTimeUpdate() {
		if (audioElement) {
			currentTime = audioElement.currentTime;
			duration = audioElement.duration || 0;
		}
	}

	function handleAudioEnded() {
		isPlaying = false;
		currentTime = 0;
	}

	function handleSeek(e: Event) {
		const target = e.target as HTMLInputElement;
		const newTime = parseFloat(target.value);
		if (audioElement) {
			audioElement.currentTime = newTime;
			currentTime = newTime;
		}
	}

	async function downloadAudio() {
		if (!audioBlobUrl || !generatedResult) return;

		savedNotification = null;
		const defaultFilename = generatedResult.filename || 'pronuncia_chinese_buddy.mp3';
		const defaultDir = '/home/simone/Musica/Sounds/';
		const defaultPath = `${defaultDir}${defaultFilename}`;
		const isTauri = '__TAURI_INTERNALS__' in window || '__TAURI__' in window;

		if (isTauri) {
			try {
				const filePath = await save({
					defaultPath: defaultPath,
					filters: [{ name: 'File Audio MP3 (*.mp3)', extensions: ['mp3'] }]
				});
				
				if (filePath) {
					const response = await fetch(audioBlobUrl);
					const buffer = await response.arrayBuffer();
					await writeFile(filePath, new Uint8Array(buffer));
					savedNotification = {
						type: 'success',
						message: 'File salvato con successo!',
						path: filePath
					};
				}
			} catch (err: any) {
				console.error("Failed to save file in Tauri:", err);
				savedNotification = {
					type: 'error',
					message: `Errore durante il salvataggio: ${err?.message || err}`
				};
			}
		} else {
			try {
				const a = document.createElement('a');
				a.href = audioBlobUrl;
				a.download = defaultFilename;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				savedNotification = {
					type: 'success',
					message: `Download avviato nel browser (${defaultFilename})`
				};
			} catch (err: any) {
				savedNotification = {
					type: 'error',
					message: `Errore durante il download: ${err?.message || err}`
				};
			}
		}
	}

	function formatTime(seconds: number): string {
		if (isNaN(seconds) || seconds < 0) return '0:00';
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
	}
</script>

<div class="w-full max-w-2xl bg-gray-900/80 backdrop-blur-md rounded-2xl border border-gray-800 shadow-2xl p-6 transition-all">
	<!-- Hidden HTML5 audio element -->
	<audio
		bind:this={audioElement}
		ontimeupdate={handleTimeUpdate}
		onloadedmetadata={handleTimeUpdate}
		onended={handleAudioEnded}
		class="hidden"
	></audio>

	<!-- Header Bar: Voice identifier & Controls (matching mockup layout) -->
	<div class="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-gray-800/80 mb-4">
		<!-- Voice indicator -->
		<div class="flex items-center gap-2.5">
			<span class="text-xl">🇨🇳</span>
			<span class="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-gray-800 text-rose-300 border border-gray-700">
				cmn-CN
			</span>
			<div class="flex items-center gap-1.5">
				<span class="text-sm font-bold text-gray-100">Xiaoxiao CN</span>
				<span class="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800/60">
					HD Femminile
				</span>
			</div>
		</div>

		<!-- Audio controls: Speed, Pitch, Volume -->
		<div class="flex items-center gap-3 text-xs text-gray-300">
			<!-- Speed / Velocità -->
			<div class="flex items-center gap-1.5 bg-gray-950/60 px-2.5 py-1 rounded-lg border border-gray-800">
				<span class="text-gray-400">Velocità:</span>
				<select
					bind:value={selectedSpeed}
					class="bg-transparent text-gray-200 font-mono text-xs focus:outline-none cursor-pointer"
				>
					<option value="0.75" class="bg-gray-900">0.75x (Lenta)</option>
					<option value="0.85" class="bg-gray-900">0.85x</option>
					<option value="1.0" class="bg-gray-900">1.0x (Normale)</option>
					<option value="1.25" class="bg-gray-900">1.25x</option>
					<option value="1.5" class="bg-gray-900">1.5x (Veloce)</option>
				</select>
			</div>

			<!-- Pitch / Tono -->
			<div class="flex items-center gap-1.5 bg-gray-950/60 px-2.5 py-1 rounded-lg border border-gray-800">
				<span class="text-gray-400">Tono:</span>
				<select
					bind:value={selectedPitch}
					class="bg-transparent text-gray-200 font-mono text-xs focus:outline-none cursor-pointer"
				>
					<option value="-1" class="bg-gray-900">-1 (Grave)</option>
					<option value="0" class="bg-gray-900">0 (Naturale)</option>
					<option value="+1" class="bg-gray-900">+1 (Acuta)</option>
				</select>
			</div>

			<!-- Volume badge -->
			<div class="hidden sm:flex items-center gap-1 bg-gray-950/60 px-2.5 py-1 rounded-lg border border-gray-800 font-mono text-gray-400">
				<span>Vol:</span>
				<span class="text-gray-200">100%</span>
			</div>
		</div>
	</div>

	<!-- Pinyin Toolbar: Quick Diacritics insertion & actions -->
	<div class="flex flex-wrap items-center justify-between gap-2 mb-3 px-1">
		<!-- Quick tone marks buttons -->
		<div class="flex flex-wrap items-center gap-1">
			<span class="text-xs text-gray-400 mr-1 hidden sm:inline">Accenti Pinyin:</span>
			{#each pinyinVowels as group}
				<div class="flex items-center bg-gray-950/70 rounded-md border border-gray-800/80 p-0.5 mr-1">
					{#each group as v}
						<button
							type="button"
							onclick={() => insertChar(v)}
							class="w-6 h-6 text-xs font-mono font-medium rounded hover:bg-rose-900/40 hover:text-rose-200 text-gray-300 transition-colors flex items-center justify-center cursor-pointer"
							title={`Inserisci ${v}`}
						>
							{v}
						</button>
					{/each}
				</div>
			{/each}
		</div>

		<!-- Action tools: Samples and Clear -->
		<div class="flex items-center gap-2">
			<!-- Quick Presets -->
			<div class="relative group">
				<button
					type="button"
					class="text-xs text-gray-400 hover:text-gray-200 bg-gray-950/60 hover:bg-gray-800/60 px-2.5 py-1 rounded-lg border border-gray-800 transition-colors flex items-center gap-1 cursor-pointer"
				>
					<span>💡 Esempi</span>
				</button>
				<div class="absolute right-0 top-full mt-1 hidden group-hover:block group-focus-within:block z-20 w-56 bg-gray-900 border border-gray-800 rounded-xl shadow-xl p-1.5 space-y-1">
					{#each samplePhrases as sample}
						<button
							type="button"
							onclick={() => applySample(sample.text)}
							class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs hover:bg-rose-950/50 hover:text-rose-200 text-gray-300 transition-colors cursor-pointer"
						>
							<div class="font-semibold text-[11px] text-gray-400">{sample.label}</div>
							<div class="font-mono text-gray-200 truncate">{sample.text}</div>
						</button>
					{/each}
				</div>
			</div>

			<!-- Clear / Trash -->
			<button
				type="button"
				onclick={clearInput}
				class="text-xs text-gray-400 hover:text-red-400 bg-gray-950/60 hover:bg-red-950/30 p-1.5 rounded-lg border border-gray-800 transition-colors cursor-pointer"
				title="Cancella testo"
			>
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
				</svg>
			</button>
		</div>
	</div>

	<!-- Text Input Area -->
	<div class="relative mb-3">
		<textarea
			bind:value={inputText}
			rows="5"
			placeholder="Scrivi qui in caratteri cinesi (es. 你好，很高兴认识你) oppure in Pinyin con accenti (nǐ hǎo) o numeri (ni3 hao3)..."
			class="w-full rounded-xl bg-gray-950/70 border border-gray-800 focus:border-rose-500 focus:ring-1 focus:ring-rose-500/40 p-4 text-gray-100 placeholder-gray-500 text-base font-normal resize-y min-h-[140px] focus:outline-none transition-all leading-relaxed"
		></textarea>
	</div>

	<!-- Bottom Info: Mode badge & Character / Word Counter -->
	<div class="flex items-center justify-between text-xs text-gray-500 mb-5 px-1 font-mono">
		<div class="flex items-center gap-1.5">
			<span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
			<span>SINTESI VOCALE AD ALTA DEFINIZIONE</span>
		</div>
		<div class="flex items-center gap-3">
			<span>{charCount} CARATTERI</span>
			<span>{wordCount} WORDS</span>
		</div>
	</div>

	<!-- Error Alert -->
	{#if errorMessage}
		<div class="mb-4 p-3 rounded-xl bg-red-950/60 border border-red-800/80 text-red-300 text-xs flex items-center gap-2">
			<span>⚠️</span>
			<span>{errorMessage}</span>
		</div>
	{/if}

	<!-- Big Generation Button (matches the mockup blue button) -->
	<button
		type="button"
		onclick={handleGenerate}
		disabled={isGenerating || !inputText.trim()}
		class="w-full py-4 px-6 rounded-xl font-bold text-sm sm:text-base tracking-wider transition-all duration-200 flex items-center justify-center gap-3 cursor-pointer shadow-lg
			{isGenerating
				? 'bg-blue-800/60 text-gray-400 cursor-not-allowed'
				: !inputText.trim()
					? 'bg-gray-800 text-gray-500 cursor-not-allowed'
					: 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/30 active:scale-[0.99]'}"
	>
		{#if isGenerating}
			<svg class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
			</svg>
			<span>GENERAZIONE AUDIO HD IN CORSO...</span>
		{:else}
			<!-- Waveform audio icon -->
			<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
				<path d="M12 2a1 1 0 0 1 1 1v18a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1zm-4 4a1 1 0 0 1 1 1v10a1 1 0 1 1-2 0V7a1 1 0 0 1 1-1zm8 0a1 1 0 0 1 1 1v10a1 1 0 1 1-2 0V7a1 1 0 0 1 1-1zm-12 4a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1zm16 0a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1z" />
			</svg>
			<span>GENERA PARLATO</span>
		{/if}
	</button>

	<!-- Result Section: Appears strictly after generation button is pressed -->
	{#if generatedResult && audioBlobUrl}
		<div class="mt-6 p-5 rounded-2xl bg-gray-950/80 border border-emerald-900/50 shadow-inner space-y-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<span class="text-base">🔊</span>
					<span class="text-xs font-bold uppercase tracking-wider text-emerald-400">
						Audio Generato con Successo
					</span>
				</div>
				<span class="text-xs font-mono text-gray-400">
					{(generatedResult.size_bytes / 1024).toFixed(1)} KB • MP3 HD
				</span>
			</div>

			<!-- Normalized/Pronounced text view -->
			{#if generatedResult.processed_text !== inputText.trim()}
				<div class="p-2.5 rounded-lg bg-gray-900/60 border border-gray-800 text-xs text-gray-300">
					<span class="text-rose-400 font-semibold">Pinyin Normalizzato:</span> {generatedResult.processed_text}
				</div>
			{/if}

			<!-- Custom Audio Player Bar -->
			<div class="flex items-center gap-3 bg-gray-900/90 p-3 rounded-xl border border-gray-800">
				<!-- Play/Pause Button -->
				<button
					type="button"
					onclick={togglePlay}
					class="w-10 h-10 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center transition-colors cursor-pointer shadow-md shadow-emerald-600/30 shrink-0"
				>
					{#if isPlaying}
						<svg class="w-4 h-4 fill-current" viewBox="0 0 24 24">
							<rect x="6" y="4" width="4" height="16" rx="1" />
							<rect x="14" y="4" width="4" height="16" rx="1" />
						</svg>
					{:else}
						<svg class="w-4 h-4 fill-current ml-0.5" viewBox="0 0 24 24">
							<polygon points="5,3 19,12 5,21" />
						</svg>
					{/if}
				</button>

				<!-- Seek progress bar -->
				<div class="flex-1 flex flex-col gap-1">
					<input
						type="range"
						min="0"
						max={duration || 100}
						step="0.05"
						value={currentTime}
						oninput={handleSeek}
						class="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
					/>
					<div class="flex justify-between text-[11px] font-mono text-gray-400">
						<span>{formatTime(currentTime)}</span>
						<span>{formatTime(duration)}</span>
					</div>
				</div>

				<!-- Download Button (explicitly accessible only after generation) -->
				<button
					type="button"
					onclick={downloadAudio}
					class="px-3.5 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-100 hover:text-white border border-gray-700 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm shrink-0"
					title="Scarica il file audio MP3 sul tuo computer"
				>
					<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
					</svg>
					<span>Scarica MP3</span>
				</button>
			</div>

			<!-- Saved Notification / Location feedback -->
			{#if savedNotification}
				<div class="p-3.5 rounded-xl text-xs flex items-start gap-2.5 transition-all shadow-md {savedNotification.type === 'success' ? 'bg-emerald-950/80 border border-emerald-700/80 text-emerald-200' : 'bg-red-950/80 border border-red-700/80 text-red-200'}">
					<span class="text-base select-none">{savedNotification.type === 'success' ? '✅' : '⚠️'}</span>
					<div class="flex-1 min-w-0">
						<p class="font-semibold text-gray-100">{savedNotification.message}</p>
						{#if savedNotification.path}
							<div class="mt-1.5 flex items-center gap-1.5">
								<span class="text-[10px] uppercase font-bold text-emerald-400/80">Percorso:</span>
								<code class="font-mono text-[11px] text-emerald-300 break-all select-all bg-emerald-900/50 px-2 py-0.5 rounded border border-emerald-800/60">
									{savedNotification.path}
								</code>
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>
