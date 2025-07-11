import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    'process.env': {},
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: ['medusa.tinyaibots.com', 'localhost', '127.0.0.1'],
  },
})
