// 后台管理接口：系统配置读取/更新、用户列表、反馈管理
import { request } from './request'
import type {
  AdminUserItem,
  PageResult,
  SystemConfig,
  SystemConfigUpdate,
  AdminFeedbackItem,
  FeedbackReply,
  FeedbackStatusUpdate,
} from '@/types'

/**
 * 获取系统配置（敏感字段脱敏）
 */
export function getSystemConfig() {
  return request<SystemConfig>({ url: '/admin/config', method: 'get' })
}

/**
 * 更新系统配置（写入 .env，需重启后端生效）
 */
export function updateSystemConfig(data: SystemConfigUpdate) {
  return request<SystemConfig>({ url: '/admin/config', method: 'put', data })
}

/**
 * 更新背景音乐 URL（立即生效；留空使用内置 mp3）
 */
export function updateBgmConfig(data: { musicUrl: string }) {
  return request<{ musicUrl: string }>({ url: '/admin/bgm', method: 'put', data })
}

/**
 * 读取当前背景音乐 URL
 */
export function getAdminBgmConfig() {
  return request<{ musicUrl: string }>({ url: '/admin/bgm', method: 'get' })
}

/**
 * 分页查询用户列表
 */
export function listUsers(params: { page?: number; pageSize?: number } = {}) {
  return request<PageResult<AdminUserItem>>({
    url: '/admin/users',
    method: 'get',
    params: { page: params.page ?? 1, page_size: params.pageSize ?? 20 },
  })
}

// ==================== 反馈管理 ====================

/**
 * 分页查询所有反馈（支持状态过滤）
 */
export function listFeedbacks(params: {
  page?: number
  pageSize?: number
  status?: string
} = {}) {
  return request<PageResult<AdminFeedbackItem>>({
    url: '/admin/feedbacks',
    method: 'get',
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
      status: params.status,
    },
  })
}

/**
 * 获取反馈详情
 */
export function getFeedbackDetail(feedbackId: string) {
  return request<AdminFeedbackItem>({
    url: `/admin/feedbacks/${feedbackId}`,
    method: 'get',
  })
}

/**
 * 回复反馈
 */
export function replyFeedback(feedbackId: string, data: FeedbackReply) {
  return request<AdminFeedbackItem>({
    url: `/admin/feedbacks/${feedbackId}/reply`,
    method: 'put',
    data,
  })
}

/**
 * 更新反馈状态
 */
export function updateFeedbackStatus(feedbackId: string, data: FeedbackStatusUpdate) {
  return request<AdminFeedbackItem>({
    url: `/admin/feedbacks/${feedbackId}/status`,
    method: 'patch',
    data,
  })
}
