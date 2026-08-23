// 反馈与建议相关接口
import { request } from './request'
import type {
  FeedbackCreate,
  FeedbackInfo,
  PageResult,
} from '@/types'

/**
 * 提交反馈与建议
 */
export function createFeedback(data: FeedbackCreate) {
  return request<FeedbackInfo>({
    url: '/feedback',
    method: 'post',
    data,
  })
}

/**
 * 获取我的反馈列表
 */
export function listMyFeedbacks(page = 1, pageSize = 20) {
  return request<PageResult<FeedbackInfo>>({
    url: '/feedback',
    method: 'get',
    params: { page, page_size: pageSize },
  })
}

/**
 * 获取反馈详情
 */
export function getMyFeedback(feedbackId: string) {
  return request<FeedbackInfo>({
    url: `/feedback/${feedbackId}`,
    method: 'get',
  })
}

/**
 * 上传单张反馈附图
 */
export function uploadFeedbackImage(file: File) {
  const formData = new FormData()
  formData.append('files', file)
  return request<string[]>({
    url: '/feedback/images',
    method: 'post',
    data: formData,
  })
}

/**
 * 上传多张反馈附图（最多5张）
 */
export function uploadFeedbackImages(files: File[]) {
  const formData = new FormData()
  files.forEach((file) => {
    formData.append('files', file)
  })
  return request<string[]>({
    url: '/feedback/images',
    method: 'post',
    data: formData,
  })
}
