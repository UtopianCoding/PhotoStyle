<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import ProfileHeader from '@/components/profile/ProfileHeader.vue'
import MyPhotosTab from '@/components/profile/MyPhotosTab.vue'
import ProfileInfoTab from '@/components/profile/ProfileInfoTab.vue'
import FeedbackTab from '@/components/profile/FeedbackTab.vue'

const userStore = useUserStore()
const activeTab = ref('photos')

// 进入页面时刷新用户信息（确保积分等数据最新）
onMounted(async () => {
  try {
    await userStore.refreshProfile()
  } catch {
    // 静默失败，store 中已有缓存数据
  }
})
</script>

<template>
  <div class="profile-page">
    <!-- 顶部个人信息卡片 -->
    <ProfileHeader />

    <!-- Tab 内容区 -->
    <div class="profile-content">
      <el-tabs v-model="activeTab" class="profile-tabs">
        <el-tab-pane label="我的照片" name="photos">
          <MyPhotosTab />
        </el-tab-pane>
        <el-tab-pane label="个人信息" name="info">
          <ProfileInfoTab />
        </el-tab-pane>
        <el-tab-pane label="意见反馈" name="feedback">
          <FeedbackTab />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  min-height: calc(100vh - 60px);
  background: var(--color-bg);
  padding: 32px 24px;
}

.profile-content {
  max-width: 1200px;
  margin: 24px auto 0;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 2px 8px rgba(156, 150, 139, 0.08),
              inset 0 1px 0 rgba(250, 248, 243, 0.5);
  position: relative;
  overflow: hidden;
}

.profile-content::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.018;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  border-radius: inherit;
}

:deep(.el-tabs__nav-wrap::after) {
  display: none;
}

:deep(.el-tabs__item) {
  font-family: var(--font-display);
  font-size: 15px;
  letter-spacing: 0.04em;
  color: var(--color-text-secondary);
  transition: all 0.3s ease;
}

:deep(.el-tabs__item:hover) {
  color: var(--color-primary);
}

:deep(.el-tabs__item.is-active) {
  color: var(--color-primary);
  font-weight: 600;
}

:deep(.el-tabs__active-bar) {
  background-color: var(--color-primary);
  height: 3px;
  border-radius: 1.5px;
}

:deep(.el-tabs__header) {
  margin-bottom: 24px;
}
</style>
