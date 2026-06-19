import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8013',
        changeOrigin: true,
        onError(err, req, res) {
          // 后端未就绪时返回 503 而非直接崩溃
          if (err.code === 'ECONNREFUSED') {
            res.writeHead(503, { 'Content-Type': 'application/json' })
            res.end(JSON.stringify({ detail: 'Backend starting, please refresh...' }))
            return
          }
          res.writeHead(500, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ detail: err.message }))
        },
      }
    }
  }
})
