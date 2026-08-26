// 3D 翻页画册 API
import { request } from './request'
import type { FlipbookProject, FlipbookPage } from '@/types/flipbook'

/** 画册列表查询参数 */
export interface FlipbookQuery {
  page?: number
  pageSize?: number
}

/** 画册列表项 */
export interface FlipbookBrief {
  projectId: string
  title: string
  kicker?: string
  status: string
  coverUrl?: string
  pageCount: number
  createdAt: string
}

/** 可用照片 */
export interface AvailablePhoto {
  resultId: string
  resultUrl: string
  thumbnailUrl: string
  taskId: string
  imageId: string
  provider: string
  createdAt: string | null
}

/** 创建画册请求 */
export interface CreateFlipbookParams {
  title: string
  kicker?: string
  resultIds: string[]
}

/** 获取可用照片列表 */
export function listAvailablePhotos(limit: number = 200) {
  return request<AvailablePhoto[]>({
    url: '/flipbook/photos',
    method: 'get',
    params: { limit },
  })
}

/** 获取背景音乐 URL（空字符串表示使用内置 mp3） */
export function getBgmConfig() {
  return request<{ musicUrl: string }>({
    url: '/flipbook/bgm',
    method: 'get',
  })
}

/** 获取画册列表 */
export function listFlipbooks(params: FlipbookQuery) {
  return request<{
    total: number
    page: number
    pageSize: number
    items: FlipbookBrief[]
  }>({
    url: '/flipbook',
    method: 'get',
    params,
  })
}

/** 获取画册详情 */
export function getFlipbook(projectId: string) {
  return request<FlipbookProject>({
    url: `/flipbook/${projectId}`,
    method: 'get',
  })
}

/** 创建画册 */
export function createFlipbook(params: CreateFlipbookParams) {
  return request<FlipbookProject>({
    url: '/flipbook',
    method: 'post',
    data: params,
    // AI 智能排序 + 创建可能耗时较长，放宽超时到 90 秒
    timeout: 90000,
  })
}

/** 删除画册 */
export function deleteFlipbook(projectId: string) {
  return request<boolean>({
    url: `/flipbook/${projectId}`,
    method: 'delete',
  })
}

/** 重新生成画册 AI 内容 */
export function regenerateFlipbook(projectId: string) {
  return request<FlipbookProject>({
    url: `/flipbook/${projectId}/regenerate`,
    method: 'post',
  })
}

/** 更新画册页面 */
export function updateFlipbookPage(
  projectId: string,
  pageId: string,
  data: { caption?: string; text?: string; fit?: string }
) {
  return request<FlipbookPage>({
    url: `/flipbook/${projectId}/pages/${pageId}`,
    method: 'put',
    params: data,
  })
}
