// 路由配置：所有页面均采用懒加载
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    // 首页：上传 + 选风格 + 转换
    component: () => import('@/views/Home.vue'),
  },
  {
    path: '/result/:id',
    name: 'Result',
    // 结果页：展示转换结果
    component: () => import('@/views/Result.vue'),
  },
  {
    path: '/history',
    name: 'History',
    // 历史记录页
    component: () => import('@/views/History.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    // 登录 / 注册页
    component: () => import('@/views/Login.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
