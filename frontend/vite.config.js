import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
      '/mesas': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/productos': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/catalog': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/gastos': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/ingresos': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  }
})
