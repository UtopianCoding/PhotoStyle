<script setup lang="ts">
// 历史记录页：按日期分组展示，支持收藏筛选、批量删除与分页加载
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Star } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import {
  batchDeleteHistory,
  deleteHistory,
  listHistory,
} from '@/api/history'
import type { HistoryItem } from '@/types'

const router = useRouter()
const loading = ref(false)
const loadingMore = ref(false)
// 历史记录列表
const items = ref<HistoryItem[]>([])
// 分页状态
const currentPage = ref(1)
const total = ref(0)
const PAGE_SIZE = 20
const hasMore = computed(() => items.value.length < total.value)
// 是否仅查看收藏
const onlyFavorite = ref(false)
// 选中的任务 ID
const selected = ref<string[]>([])

// 按收藏筛选
const filtered = computed(() => {
  if (!onlyFavorite.value) return items.value
  return items.value.filter((i) => i.hasFavorite)
})

// 按日期分组
const grouped = computed(() => {
  const map = new Map<string, HistoryItem[]>()
  filtered.value.forEach((item) => {
    const date = (item.createdAt || '').slice(0, 10) || '未知日期'
    if (!map.has(date)) map.set(date, [])
    map.get(date)!.push(item)
  })
  return Array.from(map.entries()).map(([date, list]) => ({ date, list }))
})

/** 加载历史记录（首次或刷新） */
async function load() {
  loading.value = true
  currentPage.value = 1
  try {
    const res = await listHistory({ page: 1, pageSize: PAGE_SIZE, favorite: onlyFavorite.value })
    items.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载历史失败')
  } finally {
    loading.value = false
  }
}

/** 加载更多（翻页追加） */
async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  try {
    const nextPage = currentPage.value + 1
    const res = await listHistory({ page: nextPage, pageSize: PAGE_SIZE, favorite: onlyFavorite.value })
    items.value = [...items.value, ...res.items]
    total.value = res.total
    currentPage.value = nextPage
  } catch {
    ElMessage.error('加载更多失败')
  } finally {
    loadingMore.value = false
  }
}

onMounted(load)

/** 切换收藏筛选：v-model 已更新 onlyFavorite，这里只负责重新加载 */
function onToggleFavorite() {
  load()
}

/** 收藏第一个结果 */
async function onFirstFavorite(item: HistoryItem) {
  if (item.resultThumbnails.length === 0) return
  // 简化处理：直接跳转到详情页进行收藏操作
  router.push(`/result/${item.taskId}`)
}

/** 删除单条记录 */
async function onDelete(taskId: string) {
  try {
    await ElMessageBox.confirm('确认删除该历史记录？', '提示', { type: 'warning' })
    await deleteHistory(taskId)
    ElMessage.success('已删除')
    await load()
  } catch {
    // 用户取消删除
  }
}

/** 批量删除 */
async function onBatchDelete() {
  if (selected.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selected.value.length} 条记录？`,
      '提示',
      { type: 'warning' },
    )
    await batchDeleteHistory(selected.value)
    ElMessage.success('已批量删除')
    selected.value = []
    await load()
  } catch {
    // 用户取消
  }
}

/** 打开结果详情 */
function openResult(taskId: string) {
  router.push(`/result/${taskId}`)
}
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-8">
    <!-- 顶部操作栏：宋体标题，工具靠右 -->
    <div class="history-topbar">
      <h1 class="history-topbar__title font-display">历史记录</h1>
      <div class="flex items-center gap-3">
        <el-switch v-model="onlyFavorite" active-text="仅看收藏" @change="onToggleFavorite" />
        <el-button
          :icon="Delete"
          class="history-topbar__delete"
          :disabled="selected.length === 0"
          @click="onBatchDelete"
        >
          批量删除
        </el-button>
      </div>
    </div>

    <!-- 加载中 -->
    <LoadingSkeleton v-if="loading" :rows="5" />

    <!-- 空状态 -->
    <EmptyState v-else-if="filtered.length === 0" text="暂无历史记录" />

    <!-- 列表：速写本式分组，日期用等宽字 -->
    <el-checkbox-group v-else class="history-groups" v-model="selected">
      <div v-for="group in grouped" :key="group.date" class="history-group">
        <div class="history-group__date font-mono-label">{{ group.date }}</div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div v-for="item in group.list" :key="item.taskId" class="history-card">
            <el-checkbox :value="item.taskId" class="history-card__check" />
            <!-- 3:4 竖版缩略图 -->
            <div class="history-card__img-wrap" @click="openResult(item.taskId)">
              <img
                v-if="item.resultThumbnails[0]"
                :src="item.resultThumbnails[0]"
                :alt="item.skillId"
                loading="lazy"
                decoding="async"
              />
              <img
                v-else
                :src="item.originalUrl"
                :alt="item.skillId"
                loading="lazy"
                decoding="async"
              />
              <div v-if="item.status === 'pending' || item.status === 'running'" class="history-card__mask">处理中</div>
            </div>
            <div class="history-card__bar">
              <el-button
                text
                :icon="Star"
                :type="item.hasFavorite ? 'warning' : 'default'"
                @click="onFirstFavorite(item)"
              />
              <el-button
                text
                :icon="Delete"
                class="history-card__del"
                @click="onDelete(item.taskId)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 加载更多 -->
      <div v-if="hasMore" class="history-load-more">
        <el-button
          :loading="loadingMore"
          @click="loadMore"
          class="history-load-more__btn"
        >
          {{ loadingMore ? '加载中...' : '加载更多' }}
        </el-button>
      </div>
    </el-checkbox-group>
  </div>
</template>

<style scoped>
/* 顶部栏 */
.history-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(156, 150, 139, 0.2);
}
.history-topbar__title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.08em;
}
.history-topbar__delete {
  --el-button-text-color: var(--color-text-secondary);
  --el-button-bg-color: transparent;
  --el-button-border-color: var(--color-border);
  --el-button-hover-text-color: var(--color-primary-dark);
  --el-button-hover-bg-color: transparent;
  --el-button-hover-border-color: var(--color-primary);
}

.history-groups {
  display: flex;
  flex-direction: column;
  gap: 32px;
}
.history-group__date {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
  letter-spacing: 0.05em;
}

/* 速写本卡片：茶色底、温暖边框、极淡阴影、3:4 竖版 */
.history-card {
  position: relative;
  background: var(--color-accent-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: card-fade-in 0.4s ease-out backwards;
}
.history-card:nth-child(1) { animation-delay: 0.05s; }
.history-card:nth-child(2) { animation-delay: 0.1s; }
.history-card:nth-child(3) { animation-delay: 0.15s; }
.history-card:nth-child(4) { animation-delay: 0.2s; }

.history-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(156, 150, 139, 0.2),
              0 4px 8px rgba(156, 150, 139, 0.12);
}
.history-card::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(200, 68, 43, 0.04) 100%
  );
  transition: opacity 0.3s ease;
}
.history-card:hover::after {
  opacity: 1;
}
.history-card__check {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 2;
}
/* 3:4 竖版比例，呼应技能输出 */
.history-card__img-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  cursor: pointer;
  background: var(--color-bg);
  overflow: hidden;
}
.history-card__img-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.history-card__mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  letter-spacing: 0.1em;
  background: rgba(28, 28, 26, 0.55);
}
.history-card__bar {
  display: flex;
  justify-content: space-between;
  padding: 2px 6px;
}
/* 删除按钮：温暖中性而非冷红 */
.history-card__del {
  --el-button-text-color: var(--color-text-secondary);
  --el-button-hover-text-color: var(--color-primary-dark);
}

/* 收藏星标用朱砂 */
:deep(.el-button--text.el-button--warning) {
  --el-button-text-color: var(--color-primary);
  --el-button-hover-text-color: var(--color-primary-dark);
}

@media (max-width: 640px) {
  .history-topbar__title {
    font-size: 20px;
  }
}

/* 加载更多按钮 */
.history-load-more {
  text-align: center;
  padding: 16px 0 8px;
}
.history-load-more__btn {
  --el-button-text-color: var(--color-text-secondary);
  --el-button-bg-color: transparent;
  --el-button-border-color: var(--color-border);
  --el-button-hover-text-color: var(--color-primary-dark);
  --el-button-hover-border-color: var(--color-primary);
  min-width: 120px;
}

/* 卡片入场动画 */
@keyframes card-fade-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
