import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
// v4.1 (#73): Element Plus 按需引入 — 模板组件与 API 自动解析，消除全量打包
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      dts: false,
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: false,
    }),
  ],
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
