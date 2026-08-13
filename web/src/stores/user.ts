// 用户状态管理：用户信息、token 及登录 / 登出操作
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
  const token = ref<string>(storage.getToken() ?? '')

  // 是否已登录
  const isLoggedIn = computed(() => !!token.value)

  /** 写入鉴权信息并持久化 */
  function setAuth(tokenVal: string, user: UserInfo) {
    token.value = tokenVal
    userId.value = user.userId
    email.value = user.email
    nickname.value = user.nickname
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
  async function register(nicknameVal: string, emailVal: string, password: string) {
    const res = await authApi.register({ nickname: nicknameVal, email: emailVal, password })
    setAuth(res.accessToken, res.user)
    return res
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
      storage.clear()
    }
  }

  return { userId, email, nickname, token, isLoggedIn, setAuth, login, register, logout }
})
