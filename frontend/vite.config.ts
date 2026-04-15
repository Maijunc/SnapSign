import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  // 👇 跨域代理配置就在这里 👇
  server: {
    proxy: {
      // 告诉 Vite：只要请求路径以 '/api' 开头，就帮我代理转发
      '/api': {
        target: 'http://localhost:8000', // 你真正的 FastAPI 后端地址
        changeOrigin: true,              // 允许跨域
        // 如果你的后端接口本身没有 /api 前缀，你需要把前缀重写去掉（通常 FastAPI 自己会带 /api，所以这行可以注掉）
        // rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})