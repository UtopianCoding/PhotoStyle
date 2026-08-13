<script setup lang="ts">
// 加载骨架屏组件：展示指定行数的闪烁占位条
withDefaults(
  defineProps<{
    rows?: number
  }>(),
  { rows: 3 },
)
</script>

<template>
  <div class="skeleton-list">
    <div v-for="i in rows" :key="i" class="skeleton-row"></div>
  </div>
</template>

<style scoped>
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* 骨架条：温暖茶色渐变，替代冷灰 */
.skeleton-row {
  height: 16px;
  background: linear-gradient(90deg, #e8e0d5 25%, #f0ebe2 37%, #e8e0d5 63%);
  background-size: 400% 100%;
  border-radius: var(--radius-sm);
  animation: shimmer 1.4s ease infinite;
}
@keyframes shimmer {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
</style>
