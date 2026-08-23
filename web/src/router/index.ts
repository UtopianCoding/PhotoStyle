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
    meta: { requiredPermission: 'history:view' },
  },
  {
    path: '/conversations',
    name: 'Conversations',
    // 模型交互记录页：每次与 AI 模型交互的输入/输出/提示词
    component: () => import('@/views/Conversations.vue'),
    meta: { requiredPermission: 'conversations:view' },
  },
  {
    path: '/ip-sticker',
    name: 'IPSticker',
    component: () => import('@/views/IPSticker.vue'),
    meta: { requiredPermission: 'ip_sticker:view' },
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
    // 后台配置页（需管理后台权限）
    component: () => import('@/views/Admin.vue'),
    meta: { requiredPermission: 'admin:access' },
  },
  {
    path: '/privacy',
    name: 'Privacy',
    component: () => import('@/views/Privacy.vue'),
  },
  {
    path: '/terms',
    name: 'Terms',
    component: () => import('@/views/Terms.vue'),
  },
  {
    path: '/contact',
    name: 'Contact',
    component: () => import('@/views/Contact.vue'),
  },
  {
    path: '/credits',
    name: 'Credits',
    component: () => import('@/views/Credits.vue'),
  },
  {
    path: '/profile',
    name: 'Profile',
    // 个人中心页：照片管理、个人信息编辑、意见反馈
    component: () => import('@/views/Profile.vue'),
    meta: { requiredPermission: 'profile:view' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局守卫：按权限码控制页面可见性
// - 需要某权限但当前用户不具备：未登录跳登录页，已登录跳首页
// - 管理员(is_admin)隐式拥有全部权限
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  const required = to.meta.requiredPermission as string | undefined
  if (required && !userStore.hasPermission(required)) {
    if (!userStore.isLoggedIn) {
      next('/login')
    } else {
      next('/')
    }
    return
  }
  next()
})

export default router
