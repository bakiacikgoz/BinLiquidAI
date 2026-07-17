import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const productionCsp = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' asset: http://asset.localhost data: blob:; font-src 'self' data:; connect-src ipc: http://ipc.localhost; worker-src 'self' blob:; object-src 'none'; frame-src 'none'; base-uri 'self'; form-action 'none'"

const cspSafeDependencyRoots = {
  name: 'csp-safe-dependency-roots',
  enforce: 'pre' as const,
  transform(source: string, id: string) {
    if (!id.includes('node_modules') || !source.includes("Function('return this')()")) return null
    return {
      code: source.replaceAll("Function('return this')()", 'globalThis'),
      map: null,
    }
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [cspSafeDependencyRoots, react()],
  preview: {
    headers: {
      'Content-Security-Policy': productionCsp,
    },
  },
  worker: {
    format: 'es',
  },
  test: {
    environment: 'jsdom',
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    setupFiles: ['./src/test/setup.ts'],
    globals: false,
  },
})
