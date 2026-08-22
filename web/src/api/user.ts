// 用户相关接口：个人资料更新、头像上传、权限目录、管理员编辑用户
import { request } from './request'
import type {
  AdminUserItem,
  AdminUserUpdate,
  AvatarUploadResponse,
  PermissionCatalog,
  UserUpdate,
  UserInfo,
} from '@/types'

/**
 * 更新个人资料（昵称、头像地址）
 */
export function updateMe(data: UserUpdate) {
  return request<UserInfo>({ url: '/auth/me', method: 'put', data })
}

/**
 * 上传头像，返回头像可访问地址
 */
export function uploadAvatar(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  // 注意：不要手动设置 Content-Type，axios 会在发送 FormData 时
  // 自动附带正确的 multipart/form-data 与 boundary。
  return request<AvatarUploadResponse>({
    url: '/auth/avatar',
    method: 'post',
    data: formData,
  })
}

/**
 * 获取权限目录（权限项 + 角色预设）
 */
export function getPermissionCatalog() {
  return request<PermissionCatalog>({ url: '/admin/permissions', method: 'get' })
}

/**
 * 管理员更新指定用户（昵称、头像、状态、管理员标记、权限）
 */
export function updateUser(userId: string, data: AdminUserUpdate) {
  return request<AdminUserItem>({ url: `/admin/users/${userId}`, method: 'put', data })
}
