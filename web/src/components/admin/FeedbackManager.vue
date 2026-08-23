<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listFeedbacks,
  replyFeedback,
  updateFeedbackStatus,
} from '@/api/admin'
import type { AdminFeedbackItem, FeedbackStatus } from '@/types'

// 状态
const loading = ref(false)
const feedbacks = ref<AdminFeedbackItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref<string>('')

// 回复弹窗
const replyDialogVisible = ref(false)
const replyingFeedback = ref<AdminFeedbackItem | null>(null)
const replyContent = ref('')
const replying = ref(false)

// 状态选项
const statusOptions = [
  { label: '全部', value: '' },
  { label: '待处理', value: 'pending' },
  { label: '已回复', value: 'replied' },
  { label: '已解决', value: 'resolved' },
  { label: '已关闭', value: 'closed' },
]

// 状态标签映射
const statusTagMap: Record<string, { label: string; type: 'success' | 'warning' | 'info' | 'danger' }> = {
  pending: { label: '待处理', type: 'warning' },
  replied: { label: '已回复', type: 'success' },
  resolved: { label: '已解决', type: 'success' },
  closed: { label: '已关闭', type: 'info' },
}

// 加载反馈列表
async function loadFeedbacks() {
  loading.value = true
  try {
    const res = await listFeedbacks({
      page: page.value,
      pageSize: pageSize.value,
      status: statusFilter.value || undefined,
    })
    feedbacks.value = res.items
    total.value = res.total
  } catch (error) {
    ElMessage.error('加载反馈列表失败')
  } finally {
    loading.value = false
  }
}

// 筛选状态变化
function onStatusFilterChange() {
  page.value = 1
  loadFeedbacks()
}

// 分页变化
function onPageChange(newPage: number) {
  page.value = newPage
  loadFeedbacks()
}

// 打开回复弹窗
function openReplyDialog(feedback: AdminFeedbackItem) {
  replyingFeedback.value = feedback
  replyContent.value = feedback.adminReply || ''
  replyDialogVisible.value = true
}

// 提交回复
async function submitReply() {
  if (!replyingFeedback.value) return
  if (!replyContent.value.trim()) {
    ElMessage.warning('回复内容不能为空')
    return
  }

  replying.value = true
  try {
    await replyFeedback(replyingFeedback.value.feedbackId, {
      reply: replyContent.value.trim(),
    })
    ElMessage.success('回复成功')
    replyDialogVisible.value = false
    await loadFeedbacks()
  } catch (error) {
    ElMessage.error('回复失败')
  } finally {
    replying.value = false
  }
}

// 更新状态
async function handleStatusChange(feedback: AdminFeedbackItem, newStatus: FeedbackStatus) {
  try {
    await ElMessageBox.confirm(
      `确定要将此反馈状态更改为「${statusTagMap[newStatus].label}」吗？`,
      '确认更改状态',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )

    await updateFeedbackStatus(feedback.feedbackId, { status: newStatus })
    ElMessage.success('状态已更新')
    await loadFeedbacks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('状态更新失败')
    }
  }
}

// 格式化时间
function formatTime(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 初始化
onMounted(() => {
  loadFeedbacks()
})
</script>

<template>
  <div class="feedback-manager">
    <!-- 头部工具栏 -->
    <div class="manager-toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="statusFilter"
          placeholder="筛选状态"
          clearable
          @change="onStatusFilterChange"
          style="width: 150px"
        >
          <el-option
            v-for="opt in statusOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <span class="total-count">共 {{ total }} 条反馈</span>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" :loading="loading" @click="loadFeedbacks">
          刷新
        </el-button>
      </div>
    </div>

    <!-- 反馈列表 -->
    <div v-loading="loading" class="feedback-list">
      <div v-if="feedbacks.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无反馈" />
      </div>

      <div
        v-for="feedback in feedbacks"
        :key="feedback.feedbackId"
        class="feedback-card"
      >
        <!-- 卡片头部 -->
        <div class="card-header">
          <div class="header-left">
            <el-tag :type="statusTagMap[feedback.status]?.type" size="small">
              {{ statusTagMap[feedback.status]?.label || feedback.status }}
            </el-tag>
            <span class="feedback-time">{{ formatTime(feedback.createdAt) }}</span>
          </div>
          <div class="header-right">
            <el-button
              size="small"
              type="primary"
              @click="openReplyDialog(feedback)"
            >
              {{ feedback.adminReply ? '查看回复' : '回复' }}
            </el-button>
          </div>
        </div>

        <!-- 用户信息 -->
        <div class="user-info">
          <img
            v-if="feedback.userAvatarUrl"
            :src="feedback.userAvatarUrl"
            alt="用户头像"
            class="user-avatar"
          />
          <div v-else class="user-avatar user-avatar--default">
            {{ (feedback.userNickname || feedback.userEmail || '?').charAt(0).toUpperCase() }}
          </div>
          <div class="user-meta">
            <span class="user-name">{{ feedback.userNickname || '未设置昵称' }}</span>
            <span class="user-email">{{ feedback.userEmail }}</span>
          </div>
        </div>

        <!-- 反馈内容 -->
        <div class="feedback-content">
          <p class="content-text">{{ feedback.content }}</p>
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

        <!-- 管理员回复（如果有） -->
        <div v-if="feedback.adminReply" class="admin-reply">
          <div class="reply-header">
            <span class="reply-label">管理员回复</span>
            <span class="reply-time">{{ formatTime(feedback.repliedAt!) }}</span>
          </div>
          <p class="reply-content">{{ feedback.adminReply }}</p>
        </div>

        <!-- 操作按钮 -->
        <div class="card-actions">
          <el-dropdown
            @command="(cmd: string) => handleStatusChange(feedback, cmd as FeedbackStatus)"
          >
            <el-button size="small" type="info" plain>
              更改状态
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="pending">待处理</el-dropdown-item>
                <el-dropdown-item command="replied">已回复</el-dropdown-item>
                <el-dropdown-item command="resolved">已解决</el-dropdown-item>
                <el-dropdown-item command="closed">已关闭</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="onPageChange"
      />
    </div>

    <!-- 回复弹窗 -->
    <el-dialog
      v-model="replyDialogVisible"
      :title="replyingFeedback?.adminReply ? '查看回复' : '回复反馈'"
      width="600px"
      align-center
    >
      <div v-if="replyingFeedback" class="reply-dialog">
        <!-- 用户信息 -->
        <div class="dialog-user-info">
          <img
            v-if="replyingFeedback.userAvatarUrl"
            :src="replyingFeedback.userAvatarUrl"
            alt="用户头像"
            class="user-avatar"
          />
          <div v-else class="user-avatar user-avatar--default">
            {{ (replyingFeedback.userNickname || replyingFeedback.userEmail || '?').charAt(0).toUpperCase() }}
          </div>
          <div class="user-meta">
            <span class="user-name">{{ replyingFeedback.userNickname || '未设置昵称' }}</span>
            <span class="user-email">{{ replyingFeedback.userEmail }}</span>
          </div>
        </div>

        <!-- 反馈内容 -->
        <div class="dialog-feedback-content">
          <h4>反馈内容：</h4>
          <p class="content-text">{{ replyingFeedback.content }}</p>
        </div>

        <!-- 附件图片 -->
        <div v-if="replyingFeedback.images && replyingFeedback.images.length > 0" class="dialog-feedback-images">
          <h4>附件图片：</h4>
          <div class="images-grid">
            <el-image
              v-for="(img, index) in replyingFeedback.images"
              :key="index"
              :src="img"
              :preview-src-list="replyingFeedback.images"
              :initial-index="index"
              fit="cover"
              class="feedback-image"
            />
          </div>
        </div>

        <!-- 回复输入框 -->
        <div class="reply-input">
          <h4>{{ replyingFeedback.adminReply ? '管理员回复：' : '您的回复：' }}</h4>
          <el-input
            v-model="replyContent"
            type="textarea"
            :rows="6"
            placeholder="请输入回复内容（至少10个字符）"
            maxlength="5000"
            show-word-limit
            :disabled="!!replyingFeedback.adminReply"
          />
        </div>
      </div>

      <template #footer>
        <el-button @click="replyDialogVisible = false">关闭</el-button>
        <el-button
          v-if="!replyingFeedback?.adminReply"
          type="primary"
          :loading="replying"
          :disabled="!replyContent.trim() || replyContent.trim().length < 10"
          @click="submitReply"
        >
          提交回复
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.feedback-manager {
  padding: 20px 0;
}

.manager-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.total-count {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.feedback-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 400px;
}

.empty-state {
  padding: 80px 0;
}

.feedback-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px;
  transition: box-shadow 0.2s;
}

.feedback-card:hover {
  box-shadow: 0 4px 12px rgba(156, 150, 139, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.feedback-time {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.user-avatar--default {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: white;
  font-size: 18px;
  font-weight: 600;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.user-email {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.feedback-content {
  margin-bottom: 12px;
}

.content-text {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

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

.admin-reply {
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  padding: 12px;
  margin-bottom: 12px;
}

.reply-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.reply-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
}

.reply-time {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.reply-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding: 16px;
}

/* 回复弹窗样式 */
.reply-dialog {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dialog-user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.dialog-feedback-content h4,
.dialog-feedback-images h4,
.reply-input h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 8px 0;
}

.images-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.reply-input :deep(.el-textarea__inner) {
  font-family: inherit;
}
</style>
