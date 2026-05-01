import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit(), tailwindcss()],

	// Tauri expects a fixed port – do not let Vite pick a random one
	clearScreen: false,
	server: {
		port: 1420,
		strictPort: true,
	},
});
