<script setup lang="ts">
// 根组件：顶部导航栏 + 路由出口 + 切换过渡
import { RouterLink, RouterView } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
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
          <RouterLink to="/history" class="app-nav__link">历史</RouterLink>
          <RouterLink v-if="userStore.isAdmin" to="/admin" class="app-nav__link">管理</RouterLink>
        </nav>
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
.app-main {
  min-height: calc(100vh - 60px);
}
</style>
