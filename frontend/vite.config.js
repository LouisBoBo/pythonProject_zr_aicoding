import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    // 本机 localhost / 127.0.0.1 / 局域网 IP 均可访问（勿只开后端 8009）
    host: '0.0.0.0',
    port: 5175,
    strictPort: true,
    // 避免本机 HTTP 代理把 Vite/HMR 拖死或把浏览器请求拐走
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8009',
        changeOrigin: true,
        configure(proxy) {
          proxy.on('proxyReq', (proxyReq, req) => {
            if (req.url?.includes('/chat/stream')) {
              proxyReq.setHeader('Accept', 'text/event-stream')
              proxyReq.setHeader('Cache-Control', 'no-cache')
            }
          })
          proxy.on('proxyRes', (proxyRes, req) => {
            if (!req.url?.includes('/chat/stream')) return
            delete proxyRes.headers['content-length']
            proxyRes.headers['cache-control'] = 'no-cache'
            proxyRes.headers['x-accel-buffering'] = 'no'
          })
        },
      },
      // AI 诊断中转服务（与 MES 主后端分离，默认本机 8000）
      '/ai-api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ai-api/, ''),
        timeout: 90000,
        proxyTimeout: 90000,
      },
    },
  },
})
