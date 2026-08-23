// IP 贴纸聊天相关类型定义

/** 客户端消息类型 */
export type ClientMessageType =
  | 'set_photo'
  | 'chat'
  | 'confirm_base'
  | 'modify_base'
  | 'approve_test'
  | 'regenerate_test'
  | 'generate_full'
  | 'redraw_sticker'
  | 'toggle_favorite'

/** 服务端消息类型 */
export type ServerMessageType =
  | 'session_created'
  | 'session_resumed'
  | 'chat_reply'
  | 'image_started'
  | 'image_completed'
  | 'image_grid_completed'
  | 'state_changed'
  | 'action_required'
  | 'toggle_favorite_done'
  | 'sticker_updated'
  | 'export_ready'
  | 'error'

/** 客户端 → 服务端消息 */
export interface ClientMessage {
  type: ClientMessageType
  payload: Record<string, unknown>
  request_id?: string
}

/** 服务端 → 客户端消息 */
export interface ServerMessage {
  type: ServerMessageType
  payload: Record<string, unknown>
  request_id?: string
  timestamp: string
}

/** 图片项 */
export interface ChatImage {
  url: string
  thumbnail_url?: string
  sticker_id?: string
  template_id?: string
  label?: string
  index?: number
  status?: string
  error?: string
}

/** 操作按钮 */
export interface ChatAction {
  action: string
  label: string
  type?: 'primary' | 'default' | 'danger'
  payload?: Record<string, unknown>
}

/** 显示用的聊天消息（从 ServerMessage 转换） */
export interface DisplayMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  type: string
  content?: string
  images?: ChatImage[]
  actions?: ChatAction[]
  timestamp: string
}

/** IP 母版信息 */
export interface MasterTemplate {
  templateId: string
  masterImageUrl: string
  masterThumbnailUrl?: string
  characterDescription?: string
  version: number
  isLocked: boolean
  createdAt: string
}

/** 贴纸结果 */
export interface StickerItem {
  stickerId: string
  stickerIndex: number
  label: string
  resultUrl: string
  thumbnailUrl?: string
  status: string
  batchType: string
  isFavorite: boolean
  redrawCount: number
  createdAt: string
}

/** 会话列表项 */
export interface SessionItem {
  session_id: string
  status: string
  current_step: number
  source_image_id?: string
  created_at: string
  updated_at: string
}

/** 会话详情 */
export interface SessionDetail {
  sessionId: string
  userId: string
  status: string
  currentStep: number
  sourceImageId?: string
  createdAt: string
  updatedAt: string
  messages: MessageItem[]
  masterTemplate?: MasterTemplate
  stickers: StickerItem[]
}

/** 消息项（REST API 返回） */
export interface MessageItem {
  messageId: string
  role: string
  messageType: string
  content?: string
  images?: ChatImage[]
  actions?: ChatAction[]
  sequence: number
  createdAt: string
}
