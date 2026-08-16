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
  // v4.1 (#87): vendor 分包 — 框架/图表/Markdown 库各自独立 chunk，
  // 业务代码迭代不会使这些长缓存资源失效，二次访问命中浏览器缓存
  build: {
    rollupOptions: {
      output: {
        // 注：element-plus 不做统一分组 — 按需引入下各页面只携带所需组件，
        // 统一分组会把全量组件打到首屏（实测 888KB）
        manualChunks: {
          vue: ['vue', 'vue-router'],
          d3: ['d3'],
          echarts: ['echarts'],
          markdown: ['marked', 'dompurify'],
        },
      },
    },
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
