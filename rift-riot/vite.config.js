import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

// Single self-contained HTML (no external requests) so the build can be
// opened from any static host, a LAN dev server, or straight from a file.
export default defineConfig({
  base: './',
  plugins: [viteSingleFile()],
  build: { target: 'es2020', outDir: 'dist', assetsInlineLimit: 100000000, chunkSizeWarningLimit: 4000 },
  server: { host: true },
});
