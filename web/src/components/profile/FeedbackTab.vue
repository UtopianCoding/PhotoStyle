<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import {
  listMyFeedbacks,
  createFeedback,
  uploadFeedbackImage,
} from '@/api/feedback'
import type { FeedbackInfo } from '@/types'
import { useUserStore } from '@/stores/user'
import { getCreditBalance } from '@/api/credits'

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const feedbacks = ref<FeedbackInfo[]>([])
const content = ref('')
const images = ref<string[]>([])
const uploadingImage = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

// 加载反馈列表
async function loadFeedbacks() {
  loading.value = true
  try {
    const res = await listMyFeedbacks()
    feedbacks.value = res.items
  } catch (error) {
    ElMessage.error('加载反馈列表失败')
  } finally {
    loading.value = false
  }
}

// 上传图片
async function handleImageUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  // 检查文件类型
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    target.value = ''
    return
  }

  // 检查文件大小（最大5MB）
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片大小不能超过5MB')
    target.value = ''
    return
  }

  // 检查数量限制
  if (images.value.length >= 5) {
    ElMessage.warning('最多只能上传5张图片')
    target.value = ''
    return
  }

  uploadingImage.value = true
  try {
    const res = await uploadFeedbackImage(file)
    if (res && res.length > 0) {
      images.value.push(res[0])
      ElMessage.success('图片上传成功')
    }
  } catch (error) {
    ElMessage.error('图片上传失败')
  } finally {
    uploadingImage.value = false
    target.value = ''
  }
}

// 删除图片
function removeImage(index: number) {
  images.value.splice(index, 1)
}

// 提交反馈
async function handleSubmit() {
  if (!content.value.trim()) {
    ElMessage.warning('请输入反馈内容')
    return
  }

  if (content.value.trim().length < 15) {
    ElMessage.warning('反馈内容至少需要15个字')
    return
  }

  submitting.value = true
  try {
    await createFeedback({
      content: content.value.trim(),
      images: images.value.length > 0 ? images.value : undefined,
    })
    
    // 检查是否是首次反馈（列表长度为1表示这是第一条）
    const isFirstFeedback = feedbacks.value.length === 0
    
    ElMessage.success(
      isFirstFeedback 
        ? '反馈提交成功！首次反馈奖励 3 积分已到账，感谢您的建议！'
        : '反馈提交成功，感谢您的建议！'
    )
    
    // 清空表单
    content.value = ''
    images.value = []
    
    // 重新加载列表
    await loadFeedbacks()
    
    // 刷新用户积分（首次反馈会奖励3积分）
    if (isFirstFeedback) {
      try {
        const balance = await getCreditBalance()
        userStore.updateLocalProfile({ credits: balance.credits })
      } catch (error) {
        // 积分刷新失败不影响主流程
        console.error('刷新积分失败:', error)
      }
    }
  } catch (error) {
    ElMessage.error('提交反馈失败')
  } finally {
    submitting.value = false
  }
}

// 格式化状态
function formatStatus(status: string) {
  const statusMap: Record<string, { text: string; type: 'success' | 'warning' | 'info' | 'danger' }> = {
    pending: { text: '待处理', type: 'warning' },
    replied: { text: '已回复', type: 'success' },
    resolved: { text: '已解决', type: 'success' },
    closed: { text: '已关闭', type: 'info' },
  }
  return statusMap[status] || { text: status, type: 'info' }
}

// 格式化时间
function formatTime(timeStr: string) {
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  loadFeedbacks()
})
</script>

<template>
  <div class="feedback-tab">
    <!-- 提交反馈表单 -->
    <div class="feedback-form">
      <h3 class="section-title">
        <span class="section-dot"></span>
        提交反馈
      </h3>
      <p class="form-desc">
        如果您在使用过程中遇到问题，或有功能建议，欢迎在此提交反馈。我们会尽快处理并回复您。
      </p>

      <div class="form-field">
        <label class="form-label">反馈内容</label>
        <el-input
          v-model="content"
          type="textarea"
          :rows="5"
          placeholder="请详细描述您的问题或建议（至少15个字）"
          maxlength="2000"
          show-word-limit
          resize="vertical"
        />
      </div>

      <div class="form-field">
        <label class="form-label">附件图片（可选，最多5张）</label>
        <div class="image-uploader">
          <!-- 已上传的图片 -->
          <div
            v-for="(img, index) in images"
            :key="index"
            class="image-item"
          >
            <img :src="img" alt="附件图片" />
            <button
              type="button"
              class="image-remove-btn"
              @click="removeImage(index)"
            >
              <el-icon><Delete /></el-icon>
            </button>
          </div>

          <!-- 上传按钮 -->
          <button
            v-if="images.length < 5"
            type="button"
            class="image-upload-btn"
            :class="{ 'is-uploading': uploadingImage }"
            @click="fileInput?.click()"
          >
            <template v-if="uploadingImage">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>上传中...</span>
            </template>
            <template v-else>
              <el-icon><Plus /></el-icon>
              <span>添加图片</span>
            </template>
          </button>
        </div>
        <p class="form-hint">支持 JPG/PNG 格式，单张图片不超过 5MB</p>
      </div>

      <div class="form-actions">
        <el-button
          type="primary"
          size="large"
          :loading="submitting"
          :disabled="!content.trim() || content.trim().length < 15"
          @click="handleSubmit"
          class="submit-btn"
        >
          提交反馈
        </el-button>
      </div>

      <p class="form-warning">
        <span class="form-warning__icon">!</span>
        每个账号仅首次反馈获得奖励。请勿填写密码、验证码等敏感信息。
      </p>
    </div>

    <!-- 历史反馈列表 -->
    <div class="feedback-history">
      <h3 class="section-title">
        <span class="section-dot"></span>
        我的反馈
      </h3>

      <div v-loading="loading" class="feedback-list">
        <div v-if="!loading && feedbacks.length === 0" class="empty-state">
          <el-empty description="暂无反馈记录" />
        </div>

        <div
          v-for="feedback in feedbacks"
          :key="feedback.feedbackId"
          class="feedback-card"
        >
          <!-- 头部：状态 + 时间 -->
          <div class="feedback-card__header">
            <el-tag :type="formatStatus(feedback.status).type" size="small">
              {{ formatStatus(feedback.status).text }}
            </el-tag>
            <span class="feedback-time">{{ formatTime(feedback.createdAt) }}</span>
          </div>

          <!-- 内容 -->
          <div class="feedback-card__content">
            <p class="feedback-text">{{ feedback.content }}</p>
          </div>

          <!-- 附件图片 -->
          <div v-if="feedback.images && feedback.images.length > 0" class="feedback-images">
            <el-image
              v-for="(img, index) in feedback.images"
              :key="index"
              :src="img"
              :preview-src-list="feedback.images"
              :initial-index="index"
              fit="cover"
              class="feedback-image"
            />
          </div>

          <!-- 管理员回复 -->
          <div v-if="feedback.adminReply" class="admin-reply">
            <div class="reply-header">
              <span class="reply-label">管理员回复</span>
              <span class="reply-time">{{ formatTime(feedback.repliedAt!) }}</span>
            </div>
            <p class="reply-content">{{ feedback.adminReply }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 隐藏的文件输入 -->
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      style="display: none"
      @change="handleImageUpload"
    />
  </div>
</template>

<style scoped>
.feedback-tab {
  max-width: 800px;
  margin: 0 auto;
  padding: 8px 0;
}

/* 标题样式 */
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--color-text);
  margin: 0 0 12px 0;
}

.section-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  flex-shrink: 0;
}

.form-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
  line-height: 1.6;
  margin: 0 0 20px 0;
}

/* 表单区域 */
.feedback-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 32px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 32px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--color-text);
}

.form-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
  margin: 0;
}

.form-warning {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: #c8442b;
  letter-spacing: 0.02em;
  line-height: 1.5;
  margin: 12px 0 0 0;
  padding: 8px 12px;
  background: rgba(200, 68, 43, 0.06);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(200, 68, 43, 0.12);
}

.form-warning__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 1px;
}

.form-actions {
  display: flex;
  justify-content: stretch;
}

.submit-btn {
  width: 100%;
  letter-spacing: 0.08em;
  font-size: 15px;
}

/* 图片上传器 */
.image-uploader {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.image-item {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.image-remove-btn:hover {
  background: var(--color-primary);
}

.image-upload-btn {
  width: 100px;
  height: 100px;
  border-radius: var(--radius-md);
  border: 2px dashed var(--color-border);
  background: var(--color-bg);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: var(--color-text-secondary);
  transition: all 0.2s;
}

.image-upload-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.image-upload-btn.is-uploading {
  pointer-events: none;
  opacity: 0.6;
}

.image-upload-btn span {
  font-size: 11px;
  letter-spacing: 0.02em;
}

/* 反馈历史 */
.feedback-history {
  display: flex;
  flex-direction: column;
}

.feedback-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  padding: 40px 0;
}

.feedback-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px;
  transition: box-shadow 0.2s;
}

.feedback-card:hover {
  box-shadow: 0 2px 8px rgba(156, 150, 139, 0.08);
}

.feedback-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.feedback-time {
  font-size: 12px;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
}

.feedback-card__content {
  margin-bottom: 12px;
}

.feedback-text {
  font-size: 14px;
  color: var(--color-text);
  line-height: 1.6;
  letter-spacing: 0.02em;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 反馈图片 */
.feedback-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.feedback-image {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

/* 管理员回复 */
.admin-reply {
  background: rgba(200, 68, 43, 0.04);
  border: 1px solid rgba(200, 68, 43, 0.12);
  border-radius: var(--radius-sm);
  padding: 12px;
  margin-top: 12px;
}

.reply-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.reply-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
  letter-spacing: 0.04em;
}

.reply-time {
  font-size: 11px;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
}

.reply-content {
  font-size: 13px;
  color: var(--color-text);
  line-height: 1.6;
  letter-spacing: 0.02em;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 响应式 */
@media (max-width: 640px) {
  .feedback-tab {
    padding: 8px 0;
  }

  .image-item,
  .image-upload-btn {
    width: 80px;
    height: 80px;
  }

  .feedback-image {
    width: 64px;
    height: 64px;
  }
}
</style>
