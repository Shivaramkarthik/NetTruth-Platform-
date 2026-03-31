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
        ws: true,
        timeout: 60000, // Allow up to 60s for slow speed tests
      },
    },
  },
  build: {
    // Split vendor libraries into separate cached chunks
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom')) return 'react-vendor';
            if (id.includes('framer-motion')) return 'motion';
            if (id.includes('leaflet')) return 'leaflet';
            return 'vendor';
          }
        }
      },
    },
    // Enable CSS code-splitting per lazy-loaded chunk
    cssCodeSplit: true,
    // Raise the warning threshold (video is served separately, not bundled)
    chunkSizeWarningLimit: 600,
  },
})

