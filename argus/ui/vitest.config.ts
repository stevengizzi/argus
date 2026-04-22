/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: true,
    testTimeout: 10_000,
    hookTimeout: 10_000,
    // Explicit worker pool: fork per-file, isolated jsdom environments.
    // If workers ever orphan (stuck process after a cancelled run), reap with:
    //   pkill -f 'vitest/dist/workers'
    pool: 'forks',
  },
});
