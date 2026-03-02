import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',  // 允许外部访问
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://192.168.1.143:8000',  // 使用局域网IP
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://192.168.1.143:8000',  // 使用局域网IP
        ws: true,
      },
    },
  },
})