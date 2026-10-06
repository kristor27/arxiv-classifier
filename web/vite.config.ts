import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
			},
			// A plain static site: nginx serves it and proxies /api + /ws to FastAPI.
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	// `npm run dev`: same paths as production, proxied to the API running on :8000.
	server: {
		proxy: {
			'/api': 'http://localhost:8000',
			'/ws': { target: 'ws://localhost:8000', ws: true }
		}
	}
});
