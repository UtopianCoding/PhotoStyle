// 应用入口：创建 Vue 实例并注册插件
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
// 全局样式（含 Tailwind 指令与变量）
import '@/assets/styles/main.css'

const app = createApp(App)

// 注册 Pinia 状态管理
app.use(createPinia())
// 注册路由
app.use(router)
// 注册 Element Plus
app.use(ElementPlus)

app.mount('#app')
