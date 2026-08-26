// 历史记录相关接口：列表、详情、收藏、删除、批量删除
import { request } from './request'
import type { HistoryItem, PageResult } from '@/types'

/** 历史列表查询参数 */
export interface HistoryQuery {
  page?: number
  pageSize?: number
  favorite?: boolean
  /** 起始日期 YYYY-MM-DD */
  startDate?: string
  /** 结束日期 YYYY-MM-DD */
  endDate?: string
}

/**
 * 获取历史记录列表
 */
export function listHistory(params: HistoryQuery) {
  return request<PageResult<HistoryItem>>({
    url: '/history',
    method: 'get',
    params,
  })
}

/**
 * 获取历史记录详情
 */
export function getHistoryDetail(taskId: string) {
  return request<HistoryItem>({ url: `/history/${taskId}`, method: 'get' })
}

/**
 * 收藏 / 取消收藏结果
 */
export function favoriteResult(resultId: string, favorite: boolean) {
  return request<{ resultId: string; favorite: boolean }>({
    url: `/history/${resultId}/favorite`,
    method: 'post',
    params: { favorite },
  })
}

/**
 * 删除单条历史记录
 */
export function deleteHistory(taskId: string) {
  return request<void>({ url: `/history/${taskId}`, method: 'delete' })
}

/**
 * 批量删除历史记录
 */
export function batchDeleteHistory(taskIds: string[]) {
  return request<void>({
    url: '/history/batch',
    method: 'delete',
    data: { taskIds },
  })
}
