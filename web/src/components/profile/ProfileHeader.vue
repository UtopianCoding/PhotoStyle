<script setup lang="ts">
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()

const displayName = computed(() => userStore.nickname || userStore.email || '用户')
const displayEmail = computed(() => userStore.email || '')
const avatarUrl = computed(() => userStore.avatarUrl || '')
const credits = computed(() => userStore.credits)

// 头像显示文本（取昵称首字母）
const avatarText = computed(() => {
  const name = displayName.value
  return name.charAt(0).toUpperCase()
})

function handleEditProfile() {
  ElMessage.info('请在「个人信息」标签页编辑个人资料')
}
</script>

<template>
  <div class="profile-header">
    <!-- 左侧：头像和基本信息 -->
    <div class="profile-header__left">
      <!-- 头像 -->
      <div class="profile-header__avatar">
        <img v-if="avatarUrl" :src="avatarUrl" alt="头像" class="avatar-img" />
        <div v-else class="avatar-placeholder">
          {{ avatarText }}
        </div>
      </div>

      <!-- 信息 -->
      <div class="profile-header__info">
        <h2 class="profile-header__name">{{ displayName }}</h2>
        <p class="profile-header__email">{{ displayEmail }}</p>
        <div class="profile-header__stats">
          <div class="stat-item">
            <span class="stat-label">积分余额</span>
            <span class="stat-value">{{ credits }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：操作按钮 -->
    <div class="profile-header__right">
      <el-button type="primary" @click="handleEditProfile">
        编辑资料
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.profile-header {
  max-width: 1200px;
  margin: 0 auto;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 2px 8px rgba(156, 150, 139, 0.08),
              inset 0 1px 0 rgba(250, 248, 243, 0.5);
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.profile-header::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.018;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  border-radius: inherit;
}

.profile-header__left {
  display: flex;
  align-items: center;
  gap: 20px;
  position: relative;
  z-index: 1;
}

.profile-header__avatar {
  flex-shrink: 0;
}

.avatar-img {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid var(--color-border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.avatar-placeholder {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 600;
  color: white;
  font-family: var(--font-display);
  border: 3px solid var(--color-border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.profile-header__info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.profile-header__name {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text);
  font-family: var(--font-display);
  letter-spacing: 0.02em;
  margin: 0;
}

.profile-header__email {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
  letter-spacing: 0.02em;
}

.profile-header__stats {
  display: flex;
  gap: 24px;
  margin-top: 4px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-primary);
  font-family: var(--font-display);
}

.profile-header__right {
  position: relative;
  z-index: 1;
}

@media (max-width: 640px) {
  .profile-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .profile-header__right {
    width: 100%;
  }

  .profile-header__right :deep(.el-button) {
    width: 100%;
  }
}
</style>
