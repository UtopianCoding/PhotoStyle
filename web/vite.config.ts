import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// Vite 配置：路径别名、开发代理、Element Plus 自动导入
export default defineConfig({
  plugins: [
    vue(),
    // 自动导入 Vue / Vue Router / Pinia 及 Element Plus 的 API
    AutoImport({
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [ElementPlusResolver()],
      dts: 'src/auto-imports.d.ts',
    }),
    // 自动按需注册 Element Plus 组件
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      // @ 指向 src 目录
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 7821,
    proxy: {
      // 将 /api 前缀的请求代理到后端服务
      '/api': {
        target: 'http://localhost:7823',
        changeOrigin: true,
      },
      // WebSocket 代理（IP 贴纸聊天）
      '/api/v1/ip-sticker/ws': {
        target: 'ws://localhost:7823',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
