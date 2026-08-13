<script setup lang="ts">
// 空状态组件：展示图标与提示文案
import { Box } from '@element-plus/icons-vue'

defineProps<{
  text?: string
}>()
</script>

<template>
  <div class="empty-state">
    <el-icon class="empty-state__icon"><Box /></el-icon>
    <p class="empty-state__text font-display">{{ text || '暂无数据' }}</p>
  </div>
</template>

<style scoped>
/* 空状态：石灰图标 + 宋体文案，克制安静 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
}
.empty-state__icon {
  font-size: 40px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
  opacity: 0.7;
}
.empty-state__text {
  font-size: 14px;
  color: var(--color-text-secondary);
  letter-spacing: 0.06em;
}
</style>
