<script setup lang="ts">
// 根组件：顶部导航栏 + 路由出口 + 切换过渡
import { ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, Coin, SwitchButton, User } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import ProfileDialog from '@/components/ProfileDialog.vue'
import SiteFooter from '@/components/SiteFooter.vue'

const userStore = useUserStore()
const router = useRouter()
const profileVisible = ref(false)

/** 退出登录 */
async function onLogout() {
  await userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <!-- 顶部导航：米纸底 + 温暖石灰下边框 -->
    <header class="app-header">
      <div class="app-header__inner">
        <RouterLink to="/" class="app-logo">
          <!-- 朱印：唯一签名视觉元素 -->
          <span class="app-logo__seal">影</span>
          <span class="app-logo__text">PhotoStyle</span>
        </RouterLink>
        <nav class="app-nav">
          <RouterLink to="/" class="app-nav__link">首页</RouterLink>
          <RouterLink
            v-if="userStore.hasPermission('history:view')"
            to="/history"
            class="app-nav__link"
            >历史</RouterLink
          >
          <RouterLink
            v-if="userStore.hasPermission('conversations:view')"
            to="/conversations"
            class="app-nav__link"
            >交互</RouterLink
          >
          <RouterLink
            v-if="userStore.hasPermission('ip_sticker:view')"
            to="/ip-sticker"
            class="app-nav__link"
            >表情包</RouterLink
          >
          <RouterLink
            v-if="userStore.hasPermission('admin:access')"
            to="/admin"
            class="app-nav__link"
            >管理</RouterLink
          >
        </nav>

        <!-- 右上角：未登录显示登录，已登录显示积分 + 用户菜单 -->
        <div class="app-user">
          <template v-if="userStore.isLoggedIn">
            <!-- 积分显示 -->
            <RouterLink to="/credits" class="app-credits">
              <span class="app-credits__icon">⚡</span>
              <span class="app-credits__value">{{ userStore.credits }}</span>
            </RouterLink>

            <el-dropdown trigger="click" @command="(c: string) => {
              if (c === 'profile') router.push('/profile')
              if (c === 'credits') router.push('/credits')
              if (c === 'logout') onLogout()
            }">
              <span class="app-user__trigger">
                <img
                  v-if="userStore.avatarUrl"
                  :src="userStore.avatarUrl"
                  class="app-user__avatar"
                  alt="头像"
                />
                <span v-else class="app-user__avatar app-user__avatar--default">
                  {{ (userStore.nickname || userStore.email || '?').charAt(0).toUpperCase() }}
                </span>
                <span class="app-user__name">{{ userStore.nickname || userStore.email }}</span>
                <el-icon class="app-user__caret"><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="credits">
                    <el-icon><Coin /></el-icon> 积分中心
                  </el-dropdown-item>
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon> 个人中心
                  </el-dropdown-item>
                  <el-dropdown-item command="logout" divided>
                    <el-icon><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <RouterLink v-else to="/login" class="app-user__login">登录</RouterLink>
        </div>
      </div>
    </header>

    <!-- 路由出口 -->
    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </RouterView>
    </main>

    <!-- 站脚 -->
    <SiteFooter />

    <!-- 个人资料弹窗（保留用于其他入口调用） -->
    <ProfileDialog v-model="profileVisible" />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--color-bg);
}
.app-header {
  background: rgba(245, 242, 236, 0.92);
  backdrop-filter: saturate(140%) blur(6px);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 100;
}
.app-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 16px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.app-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  transition: opacity 0.2s ease;
}
.app-logo:hover {
  opacity: 0.88;
}
/* 朱印：朱砂方印 + 白色宋体"影"字 + 轻微立体感 */
.app-logo__seal {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 20px;
  line-height: 32px;
  text-align: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-seal);
  position: relative;
}
/* 印章右下高光，模拟印泥按压不均 */
.app-logo__seal::after {
  content: "";
  position: absolute;
  right: 2px;
  bottom: 2px;
  width: 6px;
  height: 6px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 50%;
}
.app-logo__text {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.02em;
}
.app-nav {
  display: flex;
  gap: 28px;
  margin-left: auto;
}
.app-nav__link {
  color: var(--color-text-secondary);
  font-size: 14px;
  letter-spacing: 0.04em;
  transition: color 0.2s;
  position: relative;
}
/* 活跃导航项底部朱砂短横线 */
.app-nav__link.router-link-active::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: -6px;
  width: 14px;
  height: 2px;
  background: var(--color-primary);
  border-radius: 1px;
  transform: translateX(-50%);
}
.app-nav__link:hover,
.app-nav__link.router-link-active {
  color: var(--color-primary);
}

/* 积分显示 */
.app-credits {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  margin-right: 12px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  transition: all 0.2s;
}
.app-credits:hover {
  background: rgba(200, 68, 43, 0.06);
  border-color: var(--color-primary-light);
}
.app-credits__icon {
  font-size: 14px;
}
.app-credits__value {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  font-family: var(--font-mono);
}

/* 右上角用户区 */
.app-user {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.app-user__trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
  padding: 4px 6px;
  border-radius: 8px;
  transition: background 0.2s;
}
.app-user__trigger:hover {
  background: rgba(200, 68, 43, 0.06);
}
.app-user__avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}
.app-user__avatar--default {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}
.app-user__name {
  font-size: 14px;
  color: var(--color-text);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.app-user__caret {
  color: var(--color-text-secondary);
  font-size: 12px;
}
.app-user__login {
  font-size: 14px;
  color: var(--color-primary);
  letter-spacing: 0.04em;
}
.app-main {
  min-height: calc(100vh - 60px);
}
</style>
