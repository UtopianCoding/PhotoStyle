// 鉴权相关接口：注册、登录、刷新、登出、获取当前用户、发送验证码
import { request } from './request'
import type { AuthResult, LoginParams, RegisterParams, UserInfo } from '@/types'

/**
 * 发送邮箱验证码（注册前调用）
 */
export function sendVerificationCode(email: string) {
  return request<void>({ url: '/auth/send-code', method: 'post', data: { email } })
}

/**
 * 注册
 */
export function register(params: RegisterParams) {
  return request<AuthResult>({ url: '/auth/register', method: 'post', data: params })
}

/**
 * 登录
 */
export function login(params: LoginParams) {
  return request<AuthResult>({ url: '/auth/login', method: 'post', data: params })
}

/**
 * 刷新 token
 */
export function refresh(refreshToken: string) {
  return request<AuthResult>({
    url: '/auth/refresh',
    method: 'post',
    data: { refreshToken },
  })
}

/**
 * 登出
 */
export function logout() {
  return request<void>({ url: '/auth/logout', method: 'post' })
}

/**
 * 获取当前登录用户信息
 */
export function getMe() {
  return request<UserInfo>({ url: '/auth/me', method: 'get' })
}
