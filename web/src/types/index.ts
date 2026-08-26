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
  previews: string[]
  category: string
  needAnalysis: boolean
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
 * 模型服务方列表响应（含默认 provider）
 */
export interface ProvidersListResponse {
  /** 默认使用的 provider ID */
  defaultProvider: string
  /** 所有已配置 key 的 provider 列表 */
  providers: Provider[]
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
  /** 来源 Provider ID */
  provider: string
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
  /** 实际调用的 Provider 列表（多模型并行时包含多个） */
  providers?: string[]
  /** 仍在处理中的 Provider 列表 */
  pendingProviders?: string[]
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
  /** 本次生成实际使用的完整提示词（成功时返回首个结果），用于「重新生成」时回传 */
  finalPrompt?: string | null
}

/**
 * 用户信息
 */
export interface UserInfo {
  userId: string
  email: string
  nickname: string
  avatarUrl?: string
  /** 积分余额 */
  credits?: number
  /** 邀请码 */
  referralCode?: string
  /** 是否为管理员 */
  isAdmin?: boolean
  /** 权限码集合 */
  permissions?: string[]
}

/**
 * 历史记录项（对齐后端 HistoryItem）
 */
export interface HistoryItem {
  taskId: string
  skillId: string
  provider: string
  /** 实际使用的 Provider 列表（多模型并行时包含多个） */
  providers?: string[]
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
  code: string
  /** 邀请码（可选） */
  referralCode?: string
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

/**
 * 模型交互记录项（对齐后端 ConversationItem）
 * 记录每次与 AI 模型交互的输入（原图 + 提示词）与输出（结果图）
 */
export interface ConversationItem {
  interactionId: string
  taskId: string
  skillId: string
  provider: string
  inputImageUrl: string
  promptSent: string
  extraPrompt?: string | null
  feedback?: string | null
  location?: string | null
  outputImageUrls: string[]
  outputCount: number
  status: string
  errorMessage?: string | null
  durationMs?: number | null
  createdAt: string
}

/**
 * 模型交互记录详情（对齐后端 ConversationDetail，含服务商原始响应和请求体快照）
 */
export interface ConversationDetail extends ConversationItem {
  providerResponse?: string | null
  providerRequest?: string | null
}

// ============================================================
// 后台配置管理
// ============================================================

/**
 * 千问 / DashScope 配置（敏感字段脱敏）
 */
export interface DashScopeConfig {
  apiKey: string
  baseUrl: string
  modelVision: string
  modelImage: string
  workspaceId: string
  region: string
  watermark: boolean | null
  width: number | null
  height: number | null
  seed: number | null
  timeout: number | null
  promptExtend: boolean | null
}

/**
 * OpenAI / GPT Image 2 配置（敏感字段脱敏）
 */
export interface OpenAIConfig {
  apiKey: string
  baseUrl: string
  modelImage: string
  size: string | null
  resolution: string | null
  quality: string | null
  background: string | null
  outputFormat: string | null
  outputCompression: number | null
  moderation: string | null
}

/**
 * MiniMax 配置（敏感字段脱敏）
 */
export interface MinimaxConfig {
  apiKey: string
  baseUrl: string
  modelImage: string
  watermark: boolean | null
  width: number | null
  height: number | null
  seed: number | null
}

/**
 * 火山引擎（Seedream）配置（敏感字段脱敏）
 */
export interface VolcengineConfig {
  apiKey: string
  baseUrl: string
  modelImage: string
  watermark: boolean | null
  width: number | null
  height: number | null
  seed: number | null
}

/**
 * 模型配置（聚合多 provider + 默认路由）
 */
export interface ModelConfig {
  /** 默认图像生成 Provider ID：qianwen / dalle / minimax / volcengine */
  defaultProvider: string
  /** 当前启用的 Provider ID 列表（多模型并行） */
  enabledProviders: string[]
  qianwen: DashScopeConfig
  dalle: OpenAIConfig
  minimax: MinimaxConfig
  volcengine: VolcengineConfig
}

/**
 * MinIO 配置（敏感字段脱敏）
 */
export interface MinIOConfig {
  endpoint: string
  accessKey: string
  secretKey: string
  bucket: string
  secure: boolean
  publicBaseUrl: string
}

/**
 * 阿里云 OSS 配置（敏感字段脱敏）
 */
export interface OSSConfig {
  accessKeyId: string
  accessKeySecret: string
  bucket: string
  endpoint: string
}

/**
 * 存储配置（按 storageType 切换使用 minio 或 oss）
 */
export interface StorageConfig {
  /** 存储类型：minio / oss */
  storageType: string
  minio: MinIOConfig
  oss: OSSConfig
}

/**
 * 应用配置
 */
export interface AppConfigRead {
  logLevel: string
  corsAllowedOrigins: string[]
  rateLimitCreditCostPerConvert: number
  accessTokenExpireMinutes: number
}

/**
 * 系统配置（读取）
 */
export interface SystemConfig {
  model: ModelConfig
  storage: StorageConfig
  app: AppConfigRead
}

/**
 * 系统配置更新（所有字段可选，仅传入需修改的字段）
 */
export interface SystemConfigUpdate {
  model?: {
    defaultProvider?: string
    enabledProviders?: string[]
    qianwen?: {
      apiKey?: string
      baseUrl?: string
      modelVision?: string
      modelImage?: string
      workspaceId?: string
      region?: string
      watermark?: boolean | null
      width?: number | null
      height?: number | null
      seed?: number | null
      timeout?: number | null
      promptExtend?: boolean | null
    }
    dalle?: {
      apiKey?: string
      baseUrl?: string
      modelImage?: string
      size?: string | null
      resolution?: string | null
      quality?: string | null
      background?: string | null
      outputFormat?: string | null
      outputCompression?: number | null
      moderation?: string | null
    }
    minimax?: {
      apiKey?: string
      baseUrl?: string
      modelImage?: string
      watermark?: boolean | null
      width?: number | null
      height?: number | null
      seed?: number | null
    }
    volcengine?: {
      apiKey?: string
      baseUrl?: string
      modelImage?: string
      watermark?: boolean | null
      width?: number | null
      height?: number | null
      seed?: number | null
    }
  }
  storage?: {
    storageType?: string
    minio?: {
      endpoint?: string
      accessKey?: string
      secretKey?: string
      bucket?: string
      secure?: boolean
      publicBaseUrl?: string
    }
    oss?: {
      accessKeyId?: string
      accessKeySecret?: string
      bucket?: string
      endpoint?: string
    }
  }
  app?: {
    logLevel?: string
    corsAllowedOrigins?: string[]
    rateLimitCreditCostPerConvert?: number
    accessTokenExpireMinutes?: number
  }
}

/**
 * 管理员视角的用户列表项
 */
export interface AdminUserItem {
  userId: string
  email: string
  nickname: string | null
  avatarUrl?: string | null
  status: string
  isAdmin: boolean
  permissions: string[]
  credits: number
  usageToday: number
  usageLimit: number
  createdAt: string | null
}

/**
 * 个人资料更新（用户本人可修改）
 */
export interface UserUpdate {
  nickname?: string | null
  avatarUrl?: string | null
}

/**
 * 管理员更新用户（可分配权限、状态、管理员标记等）
 */
export interface AdminUserUpdate {
  nickname?: string | null
  avatarUrl?: string | null
  status?: string | null
  isAdmin?: boolean | null
  permissions?: string[] | null
}

/**
 * 权限目录项
 */
export interface PermissionItem {
  code: string
  label: string
  group: string
  description: string
}

/**
 * 角色预设
 */
export interface RolePreset {
  key: string
  label: string
  permissions: string[]
  isAdmin: boolean
}

/**
 * 权限目录响应
 */
export interface PermissionCatalog {
  permissions: PermissionItem[]
  rolePresets: RolePreset[]
}

/**
 * 头像上传响应
 */
export interface AvatarUploadResponse {
  avatarUrl: string
}

// ============================================================
// 积分系统
// ============================================================

/**
 * 积分余额响应
 */
export interface CreditBalanceResponse {
  credits: number
  referralCode: string | null
  inviteCount: number
}

/**
 * 积分交易记录项
 */
export interface CreditTransactionItem {
  transactionId: string
  transactionType: string
  amount: number
  balanceAfter: number
  description: string | null
  taskId: string | null
  relatedUserId: string | null
  createdAt: string
}

/**
 * 积分交易历史响应
 */
export interface CreditHistoryResponse {
  items: CreditTransactionItem[]
  total: number
  page: number
  pageSize: number
}

/**
 * 充值请求
 */
export interface RechargeRequest {
  amount: number
}

/**
 * 充值响应
 */
export interface RechargeResponse {
  transactionId: string
  amount: number
  newBalance: number
}

/**
 * 邀请信息响应
 */
export interface InviteInfoResponse {
  referralCode: string
  inviteCount: number
  totalRewards: number
  inviteLink: string
  rewardPerInvite: number
}

// ============================================================
// 反馈与建议
// ============================================================

/**
 * 反馈状态
 */
export type FeedbackStatus = 'pending' | 'replied' | 'resolved' | 'closed'

/**
 * 创建反馈请求
 */
export interface FeedbackCreate {
  /** 反馈内容（必填，1-2000字符） */
  content: string
  /** 附件图片URL列表（可选，最多5张） */
  images?: string[]
}

/**
 * 反馈信息（用户视角）
 */
export interface FeedbackInfo {
  feedbackId: string
  userId: string
  content: string
  images: string[] | null
  status: FeedbackStatus
  adminReply: string | null
  repliedBy: string | null
  repliedAt: string | null
  createdAt: string
  updatedAt: string
}

/**
 * 管理员回复请求
 */
export interface FeedbackReply {
  /** 回复内容（必填，1-5000字符） */
  reply: string
}

/**
 * 更新反馈状态请求
 */
export interface FeedbackStatusUpdate {
  /** 新状态 */
  status: FeedbackStatus
}

/**
 * 反馈信息（管理员视角，包含用户信息）
 */
export interface AdminFeedbackItem {
  feedbackId: string
  userId: string
  userEmail: string
  userNickname: string | null
  userAvatarUrl: string | null
  content: string
  images: string[] | null
  status: FeedbackStatus
  adminReply: string | null
  repliedBy: string | null
  repliedAt: string | null
  createdAt: string
  updatedAt: string
}
