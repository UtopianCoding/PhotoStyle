// localStorage 封装：管理 token 与用户信息
import type { UserInfo } from '@/types'

const TOKEN_KEY = 'photo_style_token'
const USER_KEY = 'photo_style_user'

export const storage = {
  /** 获取 token */
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY)
  },

  /** 设置 token */
  setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token)
  },

  /** 移除 token */
  removeToken(): void {
    localStorage.removeItem(TOKEN_KEY)
  },

  /** 获取用户信息 */
  getUser<T = UserInfo>(): T | null {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    try {
      return JSON.parse(raw) as T
    } catch {
      return null
    }
  },

  /** 设置用户信息 */
  setUser<T = UserInfo>(user: T): void {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  },

  /** 移除用户信息 */
  removeUser(): void {
    localStorage.removeItem(USER_KEY)
  },

  /** 清除所有本地凭证 */
  clear(): void {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },
}
