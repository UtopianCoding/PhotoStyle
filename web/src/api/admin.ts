// 后台管理接口：系统配置读取/更新、用户列表
import { request } from './request'
import type { AdminUserItem, PageResult, SystemConfig, SystemConfigUpdate } from '@/types'

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
 * 分页查询用户列表
 */
export function listUsers(params: { page?: number; pageSize?: number } = {}) {
  return request<PageResult<AdminUserItem>>({
    url: '/admin/users',
    method: 'get',
    params: { page: params.page ?? 1, page_size: params.pageSize ?? 20 },
  })
}
