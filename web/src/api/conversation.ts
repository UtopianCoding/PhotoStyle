// 模型交互记录相关接口：列表（分页 + 筛选）、详情
import { request } from './request'
import type { ConversationDetail, ConversationItem, PageResult } from '@/types'

/** 交互记录查询参数 */
export interface ConversationQuery {
  page?: number
  pageSize?: number
  skillId?: string | null
  status?: string | null
}

/**
 * 获取模型交互记录列表
 */
export function listConversations(params: ConversationQuery) {
  return request<PageResult<ConversationItem>>({
    url: '/conversations',
    method: 'get',
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
      skill_id: params.skillId || undefined,
      status: params.status || undefined,
    },
  })
}

/**
 * 获取交互记录详情
 */
export function getConversationDetail(interactionId: string) {
  return request<ConversationDetail>({
    url: `/conversations/${interactionId}`,
    method: 'get',
  })
}
