<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { listImages, deleteImage } from '@/api/image'
import type { ImageInfo } from '@/types'

const loading = ref(false)
const images = ref<ImageInfo[]>([])

async function loadImages() {
  loading.value = true
  try {
    const result = await listImages()
    images.value = result
  } catch (error) {
    ElMessage.error('加载图片列表失败')
  } finally {
    loading.value = false
  }
}

async function handleDelete(imageId: string) {
  try {
    await ElMessageBox.confirm('确定要删除这张图片吗？此操作不可恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })

    await deleteImage(imageId)
    ElMessage.success('图片已删除')
    
    // 从列表中移除
    images.value = images.value.filter(img => img.imageId !== imageId)
  } catch (error) {
    // 用户取消删除
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

/** 格式化文件大小，自动选择 KB 或 MB */
function formatSize(bytes: number | null) {
  if (!bytes) return '-'
  const kb = bytes / 1024
  if (kb >= 1024) {
    return (kb / 1024).toFixed(1) + ' MB'
  }
  return kb.toFixed(1) + ' KB'
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  loadImages()
})
</script>

<template>
  <div class="my-photos-tab">
    <div v-loading="loading" class="photos-container">
      <!-- 空状态 -->
      <div v-if="!loading && images.length === 0" class="empty-state">
        <el-empty description="还没有上传过图片" />
      </div>

      <!-- 图片网格 -->
      <div v-else class="photos-grid">
        <div
          v-for="image in images"
          :key="image.imageId"
          class="photo-card"
        >
          <!-- 图片预览 -->
          <div class="photo-card__preview">
            <img
              :src="image.originalUrl"
              :alt="`图片 ${image.imageId}`"
              class="preview-img"
              loading="lazy"
            />
          </div>

          <!-- 图片信息 -->
          <div class="photo-card__info">
            <div class="info-row">
              <span class="info-label">尺寸</span>
              <span class="info-value">{{ image.width }} × {{ image.height }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">大小</span>
              <span class="info-value">{{ formatSize(image.size) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">上传时间</span>
              <span class="info-value">{{ formatDate(image.createdAt) }}</span>
            </div>
            <div v-if="image.compressed && image.compressedRatio != null" class="info-row">
              <span class="info-label">已压缩</span>
              <span class="info-value info-value--compressed">{{ ((1 - image.compressedRatio) * 100).toFixed(0) }}%</span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="photo-card__actions">
            <el-button
              type="danger"
              :icon="Delete"
              size="small"
              @click="handleDelete(image.imageId)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.my-photos-tab {
  min-height: 400px;
}

.photos-container {
  min-height: 400px;
}

.empty-state {
  padding: 80px 0;
}

.photos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  padding: 8px 0;
}

.photo-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all 0.3s ease;
  position: relative;
}

.photo-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(156, 150, 139, 0.15);
  border-color: var(--color-primary);
}

.photo-card__preview {
  aspect-ratio: 1;
  background: var(--color-bg);
  overflow: hidden;
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.photo-card:hover .preview-img {
  transform: scale(1.05);
}

.photo-card__info {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.info-label {
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
}

.info-value {
  color: var(--color-text);
  font-family: var(--font-mono);
  font-weight: 500;
}

.info-value--compressed {
  color: var(--color-success);
}

.photo-card__actions {
  padding: 12px;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .photos-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .photos-grid {
    grid-template-columns: 1fr;
  }
}
</style>
