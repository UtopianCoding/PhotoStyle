// 路由配置：所有页面均采用懒加载，并通过全局守卫保护需登录/管理员页面
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

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
  {
    path: '/admin',
    name: 'Admin',
    // 后台配置页（仅管理员可访问）
    component: () => import('@/views/Admin.vue'),
    meta: { requiresAdmin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局守卫：未登录访问需登录页 → 跳登录；非管理员访问 admin → 跳首页
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    next('/')
    return
  }
  next()
})

export default router
