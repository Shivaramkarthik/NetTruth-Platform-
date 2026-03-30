import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 60000, // Allow up to 60s for slow speed tests
      },
    },
  },
  build: {
    // Split vendor libraries into separate cached chunks
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor':  ['react', 'react-dom'],
          'motion':        ['framer-motion'],
          'leaflet':       ['leaflet'],
        },
      },
    },
    // Enable CSS code-splitting per lazy-loaded chunk
    cssCodeSplit: true,
    // Raise the warning threshold (video is served separately, not bundled)
    chunkSizeWarningLimit: 600,
  },
})

