// IP 贴纸 REST API（会话列表、详情）
import { request } from './request'
import type { SessionItem, SessionDetail } from '@/types/ipSticker'

/** 会话列表 */
export async function listIPSessions() {
  return request<{ sessions: SessionItem[] }>({
    url: '/ip-sticker/sessions',
    method: 'get',
  })
}

/** 会话详情（含消息历史、母版、贴纸） */
export async function getSessionDetail(sessionId: string) {
  return request<SessionDetail>({
    url: `/ip-sticker/sessions/${sessionId}`,
    method: 'get',
  })
}
