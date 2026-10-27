import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// Versão do app, injetada no build (CI/Docker passam APP_VERSION). Padrão "dev".
const appVersion = process.env.APP_VERSION || 'dev'

// Gera dist/version.json -> {"version": "<APP_VERSION>"}
function versionFile(): Plugin {
  return {
    name: 'version-file',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'version.json',
        source: JSON.stringify({ version: appVersion }),
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), versionFile()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
  },
  server: {
    proxy: {
      // A API já responde sob /api: /api/health -> http://localhost:8000/api/health
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
