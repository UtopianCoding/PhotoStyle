// 全局 TypeScript 类型定义
// 所有类型与后端 API camelCase 响应对齐

/**
 * 统一 API 响应结构
 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

/**
 * 图片信息（对齐后端 ImageUploadResponse / ImageInfo）
 */
export interface ImageInfo {
  imageId: string
  originalUrl: string
  thumbnailUrl: string | null
  mimeType: string
  width: number | null
  height: number | null
  size: number | null
  compressed: boolean
  compressedRatio: number | null
  createdAt: string | null
}

/**
 * 风格技能
 */
export interface Skill {
  id: string
  name: string
  description: string
  preview: string
  category: string
}

/**
 * 模型服务方
 */
export interface Provider {
  id: string
  name: string
  models: string[]
}

/**
 * 任务状态
 */
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'canceled'

/**
 * 风格转换结果（对齐后端 TaskResult）
 */
export interface StyleResult {
  resultId: string
  resultUrl: string
  thumbnailUrl: string | null
  favorite: boolean
  createdAt: string | null
}

/**
 * 图片分析结果（对齐后端 AnalyzeResponse）
 */
export interface AnalysisResult {
  /** 推荐使用的技能 ID（city-editorial 或 photo-revival） */
  recommendedSkillId: string
  subjectAnalysis: string
  coreElements: string[]
  rules: {
    composition?: string
    mainArea?: string
    negativeSpace?: string
    topHalf?: string
    bottomHalf?: string
    typography?: string
    style?: string
    colors?: string[]
    textNote?: string
    avoid?: string
  }
  specialNotes: string
  finalPrompt: string
  poeticOptions: string[]
  suggestions: string[]
}

/**
 * 风格转换任务（对齐后端 ConvertResponse / TaskStatusResponse）
 * 合并了提交响应和状态查询响应的字段
 */
export interface StyleTask {
  taskId: string
  imageId: string
  /** 原图地址（状态接口轮询返回，前端结果页独立使用） */
  originalUrl: string
  skillId: string
  provider: string
  extraPrompt?: string | null
  options?: Record<string, unknown>
  status: TaskStatus
  progress: number
  stage?: string | null
  message?: string | null
  error?: string | null
  results?: StyleResult[]
  estimatedTime?: number
  createdAt?: string | null
  updatedAt?: string | null
}

/**
 * 用户信息
 */
export interface UserInfo {
  userId: string
  email: string
  nickname: string
  avatarUrl?: string
}

/**
 * 历史记录项（对齐后端 HistoryItem）
 */
export interface HistoryItem {
  taskId: string
  skillId: string
  provider: string
  imageId: string
  originalUrl: string
  status: string
  resultThumbnails: string[]
  hasFavorite: boolean
  createdAt: string
}

/**
 * 登录参数
 */
export interface LoginParams {
  email: string
  password: string
}

/**
 * 注册参数
 */
export interface RegisterParams extends LoginParams {
  nickname: string
}

/**
 * 鉴权结果
 */
export interface AuthResult {
  accessToken: string
  refreshToken: string
  tokenType: string
  expiresIn: number
  user: UserInfo
}

/**
 * 分页结果
 */
export interface PageResult<T> {
  items: T[]
  total: number
}
