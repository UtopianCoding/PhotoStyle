// 用户状态管理：用户信息、token 及登录 / 登出 / 权限操作
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types'
import { storage } from '@/utils/storage'
import * as authApi from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  // 从本地存储恢复用户信息
  const stored = storage.getUser<UserInfo>()
  const userId = ref<string>(stored?.userId ?? '')
  const email = ref<string>(stored?.email ?? '')
  const nickname = ref<string>(stored?.nickname ?? '')
  const avatarUrl = ref<string>(stored?.avatarUrl ?? '')
  const credits = ref<number>(stored?.credits ?? 0)
  const referralCode = ref<string>(stored?.referralCode ?? '')
  const isAdmin = ref<boolean>(stored?.isAdmin ?? false)
  const permissions = ref<string[]>(stored?.permissions ?? [])
  const token = ref<string>(storage.getToken() ?? '')

  // 是否已登录
  const isLoggedIn = computed(() => !!token.value)

  /** 判断当前用户是否拥有某权限（管理员隐式拥有全部权限） */
  function hasPermission(code: string): boolean {
    if (isAdmin.value) return true
    return permissions.value.includes(code)
  }

  /** 写入鉴权信息并持久化 */
  function setAuth(tokenVal: string, user: UserInfo) {
    token.value = tokenVal
    userId.value = user.userId
    email.value = user.email
    nickname.value = user.nickname
    avatarUrl.value = user.avatarUrl ?? ''
    credits.value = user.credits ?? 0
    referralCode.value = user.referralCode ?? ''
    isAdmin.value = user.isAdmin ?? false
    permissions.value = user.permissions ?? []
    storage.setToken(tokenVal)
    storage.setUser(user)
  }

  /** 登录 */
  async function login(emailVal: string, password: string) {
    const res = await authApi.login({ email: emailVal, password })
    setAuth(res.accessToken, res.user)
    return res
  }

  /** 注册 */
  async function register(emailVal: string, password: string, code: string, nicknameVal: string, referralCodeVal?: string) {
    const res = await authApi.register({ email: emailVal, password, code, nickname: nicknameVal, referralCode: referralCodeVal })
    setAuth(res.accessToken, res.user)
    return res
  }

  /** 登录后刷新用户信息（含最新权限），用于权限变更后同步 */
  async function refreshProfile() {
    const res = await authApi.getMe()
    nickname.value = res.nickname
    avatarUrl.value = res.avatarUrl ?? ''
    credits.value = res.credits ?? 0
    referralCode.value = res.referralCode ?? ''
    isAdmin.value = res.isAdmin ?? false
    permissions.value = res.permissions ?? []
    // 同步本地持久化
    const persisted = storage.getUser<UserInfo>()
    if (persisted) {
      storage.setUser({ ...persisted, ...res })
    }
    return res
  }

  /** 本地更新个人资料（昵称、头像、积分），不触发重新拉取 */
  function updateLocalProfile(partial: Partial<UserInfo>) {
    if (partial.nickname !== undefined) nickname.value = partial.nickname
    if (partial.avatarUrl !== undefined) avatarUrl.value = partial.avatarUrl ?? ''
    if (partial.credits !== undefined) credits.value = partial.credits
    if (partial.referralCode !== undefined) referralCode.value = partial.referralCode ?? ''
    if (partial.permissions !== undefined) permissions.value = partial.permissions
    if (partial.isAdmin !== undefined) isAdmin.value = partial.isAdmin
    const persisted = storage.getUser<UserInfo>()
    if (persisted) {
      storage.setUser({ ...persisted, ...partial })
    }
  }

  /** 登出 */
  async function logout() {
    try {
      await authApi.logout()
    } finally {
      token.value = ''
      userId.value = ''
      email.value = ''
      nickname.value = ''
      avatarUrl.value = ''
      credits.value = 0
      referralCode.value = ''
      isAdmin.value = false
      permissions.value = []
      storage.clear()
    }
  }

  return {
    userId,
    email,
    nickname,
    avatarUrl,
    credits,
    referralCode,
    isAdmin,
    permissions,
    token,
    isLoggedIn,
    hasPermission,
    setAuth,
    login,
    register,
    refreshProfile,
    updateLocalProfile,
    logout,
  }
})
