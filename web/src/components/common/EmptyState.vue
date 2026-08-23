<script setup lang="ts">
// 空状态组件：诗意留白，呼应宣纸美学
import { Box } from '@element-plus/icons-vue'

defineProps<{
  text?: string
}>()
</script>

<template>
  <div class="empty-state">
    <!-- 水墨晕染装饰 -->
    <div class="empty-state__art">
      <div class="empty-state__circle"></div>
      <div class="empty-state__circle empty-state__circle--sm"></div>
      <el-icon class="empty-state__icon"><Box /></el-icon>
    </div>
    <p class="empty-state__text font-display">{{ text || '暂无数据' }}</p>
    <div class="empty-state__ink-line"></div>
  </div>
</template>

<style scoped>
/* 空状态：诗意留白，水墨晕染 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 56px 0;
  animation: empty-fade-in 0.5s ease-out;
}

/* 水墨艺术装饰：双层晕染圆 */
.empty-state__art {
  position: relative;
  width: 72px;
  height: 72px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-state__circle {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(156, 150, 139, 0.12) 0%,
    rgba(156, 150, 139, 0.04) 50%,
    transparent 70%
  );
  animation: ink-breathe 3s ease-in-out infinite;
}
.empty-state__circle--sm {
  width: 70%;
  height: 70%;
  background: radial-gradient(
    circle,
    rgba(200, 68, 43, 0.08) 0%,
    rgba(200, 68, 43, 0.02) 60%,
    transparent 80%
  );
  animation-delay: 0.5s;
}

.empty-state__icon {
  position: relative;
  z-index: 1;
  font-size: 28px;
  color: var(--color-text-secondary);
  opacity: 0.65;
}

.empty-state__text {
  font-size: 14px;
  color: var(--color-text-secondary);
  letter-spacing: 0.06em;
  margin: 0 0 20px;
}

/* 底部墨线：收束留白 */
.empty-state__ink-line {
  width: 48px;
  height: 2px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(156, 150, 139, 0.3) 20%,
    rgba(156, 150, 139, 0.3) 80%,
    transparent
  );
  border-radius: 1px;
}

@keyframes empty-fade-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes ink-breathe {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.08);
    opacity: 0.7;
  }
}
</style>
