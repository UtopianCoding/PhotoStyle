// 技能与模型服务方相关接口
import { request } from './request'
import type { Provider, Skill } from '@/types'

/**
 * 获取风格技能列表
 */
export function listSkills() {
  return request<Skill[]>({ url: '/skills', method: 'get' })
}

/**
 * 获取模型服务方列表
 */
export function listProviders() {
  return request<Provider[]>({ url: '/providers', method: 'get' })
}
