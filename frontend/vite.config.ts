import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { writeFileSync } from 'fs';
import { resolve } from 'path';

// Generate version.json with build timestamp so browsers can detect new deploys
function versionPlugin() {
  return {
    name: 'version-plugin',
    closeBundle() {
      writeFileSync(
        resolve(__dirname, 'dist', 'version.json'),
        JSON.stringify({ v: Date.now() }),
      );
    },
  };
}

export default defineConfig({
  plugins: [react(), versionPlugin()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
