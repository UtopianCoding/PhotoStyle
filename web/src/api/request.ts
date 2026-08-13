// Axios 实例与请求封装：附带鉴权、统一错误处理、业务数据解包
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { storage } from '@/utils/storage'
import type { ApiResponse } from '@/types'

const service: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 请求拦截器：附加鉴权 token
service.interceptors.request.use(
  (config) => {
    const token = storage.getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器：统一处理 HTTP 错误
service.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      storage.clear()
      ElMessage.error('登录已过期，请重新登录')
      window.location.href = '/login'
    } else {
      ElMessage.error(error?.response?.data?.message || error?.message || '网络错误')
    }
    return Promise.reject(error)
  },
)

/**
 * 业务请求封装：自动解包 ApiResponse.data
 * @param config Axios 请求配置
 */
export async function request<T = unknown>(config: AxiosRequestConfig): Promise<T> {
  const response: AxiosResponse<ApiResponse<T>> = await service(config)
  const body = response.data
  // 非标准结构（如二进制流）直接返回
  if (!body || typeof body !== 'object' || !('code' in body)) {
    return body as unknown as T
  }
  // 业务错误
  if (body.code !== 0 && body.code !== 200) {
    ElMessage.error(body.message || '请求失败')
    return Promise.reject(new Error(body.message || '请求失败'))
  }
  return body.data
}

export default service
