import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';
import basicSsl from '@vitejs/plugin-basic-ssl';

export default defineConfig({
	plugins: [sveltekit(), tailwindcss(), basicSsl()],

	// Tauri expects a fixed port – do not let Vite pick a random one
	clearScreen: false,
	server: {
		port: 1420,
		strictPort: true,
		proxy: {
			'/ws': {
				target: 'ws://localhost:8000',
				ws: true,
			},
		},
	},
});
