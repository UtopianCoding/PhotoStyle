// IP 贴纸聊天 WebSocket 管理 — 支持多会话切换
import { ref, reactive, onUnmounted, nextTick, watch } from 'vue'
import { storage } from '@/utils/storage'
import type {
  ServerMessage,
  ClientMessageType,
  DisplayMessage,
} from '@/types/ipSticker'

const SESSION_KEY = 'ip_sticker_session_id'

let _uid = 0
function uid() { return `msg_${++_uid}_${Date.now()}` }

export function useIPStickerChat() {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const messages = ref<DisplayMessage[]>([])
  const sessionId = ref('')
  const sessionStatus = ref('')
  const currentStep = ref(0)
  const generating = ref(false)

  let reconnectTimer: number | null = null
  let reconnectAttempts = 0
  const MAX_RECONNECT = 5

  // 持久化当前 sessionId
  watch(sessionId, (val) => {
    if (val) localStorage.setItem(SESSION_KEY, val)
    else localStorage.removeItem(SESSION_KEY)
  })

  function scrollToBottom() {
    nextTick(() => {
      const el = document.querySelector('.chat-window')
      if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    })
  }

  function connect(sid?: string) {
    disconnect()

    const token = storage.getToken()
    if (!token) return

    const resumeSid = sid || localStorage.getItem(SESSION_KEY) || undefined

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const params = new URLSearchParams({ token })
    if (resumeSid) params.set('session_id', resumeSid)

    const wsUrl = `${proto}//${location.host}/api/v1/ip-sticker/ws?${params}`
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      connected.value = true
      reconnectAttempts = 0
      // 刷新消息队列
      while (pendingQueue.length > 0) {
        ws.value!.send(pendingQueue.shift()!)
      }
    }

    ws.value.onmessage = (event) => {
      try {
        const msg: ServerMessage = JSON.parse(event.data)
        handleMessage(msg)
      } catch { /* ignore parse errors */ }
    }

    ws.value.onclose = () => {
      connected.value = false
      ws.value = null
      // 只对有 sessionId 的会话重连
      if (sessionId.value) {
        scheduleReconnect(sessionId.value)
      }
    }

    ws.value.onerror = () => {
      ws.value?.close()
    }
  }

  function handleMessage(msg: ServerMessage) {
    switch (msg.type) {
      case 'session_created':
        sessionId.value = msg.payload.session_id as string
        sessionStatus.value = msg.payload.status as string
        currentStep.value = msg.payload.step as number
        break

      case 'session_resumed': {
        sessionId.value = msg.payload.session_id as string
        sessionStatus.value = msg.payload.status as string
        currentStep.value = msg.payload.step as number
        const history = msg.payload.history as Array<{
          message_id: string
          role: string
          message_type: string
          content?: string
          images?: Array<Record<string, unknown>>
          actions?: Array<Record<string, unknown>>
          sequence: number
          created_at?: string
        }>
        if (history?.length) {
          messages.value = history.map((h) => ({
            id: h.message_id,
            role: h.role as 'user' | 'assistant',
            type: h.message_type,
            content: h.content || undefined,
            images: h.images as DisplayMessage['images'],
            actions: h.actions as DisplayMessage['actions'],
            timestamp: h.created_at || '',
          }))
        } else {
          messages.value = []
        }
        scrollToBottom()
        break
      }

      case 'chat_reply':
        messages.value.push({
          id: uid(),
          role: 'assistant',
          type: 'text',
          content: msg.payload.text as string,
          timestamp: msg.timestamp,
        })
        break

      case 'image_started':
        generating.value = true
        messages.value.push({
          id: uid(),
          role: 'assistant',
          type: 'image_generating',
          content: msg.payload.hint as string,
          timestamp: msg.timestamp,
        })
        break

      case 'image_completed': {
        generating.value = false
        const images = msg.payload.images as DisplayMessage['images']
        const message = msg.payload.message as string | undefined
        const actions = msg.payload.actions as DisplayMessage['actions']
        messages.value = messages.value.filter((m) => m.type !== 'image_generating')
        if (message) {
          messages.value.push({
            id: uid(), role: 'assistant', type: 'text',
            content: message, timestamp: msg.timestamp,
          })
        }
        messages.value.push({
          id: uid(), role: 'assistant', type: 'image_single',
          images, actions, timestamp: msg.timestamp,
        })
        break
      }

      case 'image_grid_completed': {
        generating.value = false
        const images = msg.payload.images as DisplayMessage['images']
        const message = msg.payload.message as string | undefined
        const actions = msg.payload.actions as DisplayMessage['actions']
        messages.value = messages.value.filter((m) => m.type !== 'image_generating')
        if (message) {
          messages.value.push({
            id: uid(), role: 'assistant', type: 'text',
            content: message, timestamp: msg.timestamp,
          })
        }
        messages.value.push({
          id: uid(), role: 'assistant', type: 'image_grid',
          images, actions, timestamp: msg.timestamp,
        })
        break
      }

      case 'state_changed':
        sessionStatus.value = msg.payload.status as string
        currentStep.value = msg.payload.step as number
        break

      case 'error':
        generating.value = false
        messages.value = messages.value.filter((m) => m.type !== 'image_generating')
        messages.value.push({
          id: uid(), role: 'assistant', type: 'error',
          content: msg.payload.message as string, timestamp: msg.timestamp,
        })
        break

      case 'action_required': {
        const message = msg.payload.message as string | undefined
        const actions = msg.payload.actions as DisplayMessage['actions']
        if (message) {
          messages.value.push({
            id: uid(), role: 'assistant', type: 'text',
            content: message, timestamp: msg.timestamp,
          })
        }
        if (actions?.length) {
          messages.value.push({
            id: uid(), role: 'assistant', type: 'actions',
            actions, timestamp: msg.timestamp,
          })
        }
        break
      }

      case 'toggle_favorite_done':
        break
    }

    scrollToBottom()
  }

  // 消息队列：连接未就绪时暂存消息，onopen 时自动发送
  const pendingQueue: string[] = []

  function send(type: ClientMessageType, payload: Record<string, unknown> = {}) {
    const data = JSON.stringify({ type, payload, request_id: crypto.randomUUID() })
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(data)
    } else {
      // 连接未就绪，加入队列等待发送
      pendingQueue.push(data)
      // 如果还没连接，自动发起连接
      if (!ws.value || ws.value.readyState === WebSocket.CLOSED) {
        connect()
      }
    }
  }

  function sendText(text: string) {
    messages.value.push({
      id: uid(), role: 'user', type: 'text',
      content: text, timestamp: new Date().toISOString(),
    })
    scrollToBottom()
    send('chat', { text })
  }

  function sendPhoto(imageId: string, imageUrl?: string) {
    messages.value.push({
      id: uid(), role: 'user', type: 'image_single',
      content: '上传了一张照片',
      images: imageUrl ? [{ url: imageUrl, thumbnail_url: imageUrl, label: '我的照片' }] : [],
      timestamp: new Date().toISOString(),
    })
    scrollToBottom()
    send('set_photo', { image_id: imageId })
  }

  function sendAction(action: string, extra: Record<string, unknown> = {}) {
    messages.value.push({
      id: uid(), role: 'user', type: 'text',
      content: (extra._label as string) || action,
      timestamp: new Date().toISOString(),
    })
    scrollToBottom()
    const { _label, ...payload } = extra
    send(action as ClientMessageType, payload)
  }

  /** 切换到指定会话（断开当前连接 → 清空消息 → 重连指定会话） */
  function switchSession(sid: string) {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectAttempts = 0
    messages.value = []
    generating.value = false
    sessionStatus.value = ''
    currentStep.value = 0
    connect(sid)
  }

  /** 创建全新会话（仅清空本地状态，延迟到发送消息时才建后端 session） */
  function newSession() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectAttempts = 0
    messages.value = []
    generating.value = false
    sessionId.value = ''
    sessionStatus.value = ''
    currentStep.value = 0
    localStorage.removeItem(SESSION_KEY)
    // 断开旧连接（如果有的话）
    disconnect()
  }

  function scheduleReconnect(sid: string) {
    if (reconnectAttempts >= MAX_RECONNECT) return
    reconnectAttempts++
    const delay = Math.min(1000 * 2 ** reconnectAttempts, 30000)
    reconnectTimer = window.setTimeout(() => connect(sid), delay)
  }

  function disconnect() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    reconnectAttempts = 0
    ws.value?.close()
    ws.value = null
  }

  function reset() {
    disconnect()
    messages.value = []
    sessionId.value = ''
    sessionStatus.value = ''
    currentStep.value = 0
    generating.value = false
    localStorage.removeItem(SESSION_KEY)
  }

  onUnmounted(disconnect)

  return reactive({
    connected, messages, sessionId, sessionStatus, currentStep, generating,
    connect, disconnect, send, sendText, sendPhoto, sendAction,
    switchSession, newSession, reset,
  })
}
