// 分享海报生成工具
// 纯前端基于 canvas 绘制：效果图 + 朱砂边框 + 标题 + 二维码（扫码跳本站）
// 关键点：用 fetch→blob→objectURL 加载图片再 drawImage，可避免 canvas 被跨域污染，
// 从而能正常调用 toDataURL 导出海报。

import QRCode from 'qrcode'

export interface PosterOptions {
  /** 要展示的效果图地址 */
  imageUrl: string
  /** 二维码编码的链接（默认当前结果页，扫码即跳转到本站该作品） */
  shareUrl: string
  /** 站点名（左上角主标题） */
  siteName?: string
  /** 副标题 */
  subtitle?: string
}

// 水墨纸砚配色，与全局设计系统保持一致
const PAPER = '#f5f2ec'
const PAPER_CARD = '#ffffff'
const INK = '#2b2620'
const INK_SOFT = '#6b655b'
const CINNABAR = '#c8442b'
const BORDER = 'rgba(156,150,139,0.35)'

/** 加载图片（用于同源 dataURL / objectURL，不污染 canvas） */
function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('图片加载失败'))
    img.src = src
  })
}

/** 跨域安全加载：fetch→blob→objectURL，绘制后不会污染 canvas */
async function loadImageClean(url: string): Promise<HTMLImageElement | null> {
  try {
    const resp = await fetch(url, { mode: 'cors' })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const blob = await resp.blob()
    const objUrl = URL.createObjectURL(blob)
    const img = await loadImage(objUrl)
    // onload 后位图已就绪，可安全释放 objectURL
    URL.revokeObjectURL(objUrl)
    return img
  } catch {
    return null
  }
}

/** 圆角矩形路径 */
function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

/** 取链接的 host 用于海报文案展示 */
function safeHost(url: string): string {
  try {
    return new URL(url).host
  } catch {
    return location.host
  }
}

/**
 * 生成分享海报，返回 PNG 的 dataURL。
 */
export async function generateSharePoster(opts: PosterOptions): Promise<string> {
  // 等待品牌字体就绪，避免文字回退为系统字体
  if (document.fonts?.ready) {
    try {
      await document.fonts.ready
    } catch {
      /* 忽略字体等待失败 */
    }
  }

  const scale = 2 // 2x 渲染保证清晰度
  const W = 1080
  const margin = 60
  const contentTop = 200
  const imgW = W - margin * 2

  // 先加载效果图：按原图比例动态计算卡片高度，保证整图完整展示、不被裁切
  const img = await loadImageClean(opts.imageUrl)
  const rawW = img?.width || imgW
  const rawH = img?.height || 1200
  // 卡片宽度固定为 imgW，高度随原图比例伸缩（限制在 480~1440，防止过长/过扁）
  const imgH = Math.min(1440, Math.max(480, Math.round((imgW * rawH) / rawW)))

  const bottomH = 300
  const H = contentTop + imgH + 40 + bottomH

  const canvas = document.createElement('canvas')
  canvas.width = W * scale
  canvas.height = H * scale
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('无法创建 canvas 上下文')
  ctx.scale(scale, scale)

  const serif = '"Noto Serif SC", "Songti SC", "STSong", serif'

  // 背景：米纸
  ctx.fillStyle = PAPER
  ctx.fillRect(0, 0, W, H)

  // 外框：朱砂
  ctx.strokeStyle = CINNABAR
  ctx.lineWidth = 3
  ctx.strokeRect(margin - 18, margin - 18, W - (margin - 18) * 2, H - (margin - 18) * 2)
  // 内细框：暖石灰
  ctx.strokeStyle = BORDER
  ctx.lineWidth = 1
  ctx.strokeRect(margin - 8, margin - 8, W - (margin - 8) * 2, H - (margin - 8) * 2)

  // 顶部标题区
  ctx.textBaseline = 'middle'
  const sealSize = 56
  ctx.fillStyle = CINNABAR
  roundRect(ctx, margin, 50, sealSize, sealSize, 8)
  ctx.fill()
  ctx.fillStyle = '#ffffff'
  ctx.textAlign = 'center'
  ctx.font = `700 26px ${serif}`
  ctx.fillText('照', margin + sealSize / 2, 50 + sealSize / 2 + 1)

  ctx.textAlign = 'left'
  ctx.fillStyle = INK
  ctx.font = `700 38px ${serif}`
  ctx.fillText(opts.siteName || 'PhotoStyle', margin + sealSize + 18, 70)
  ctx.fillStyle = INK_SOFT
  ctx.font = `400 18px ${serif}`
  ctx.fillText(opts.subtitle || 'AI 影像风格 · 转换结果', margin + sealSize + 18, 102)

  // 效果图卡片：卡片比例与原图一致，整图放入（不裁剪）
  const bottomY = contentTop + imgH + 40
  ctx.fillStyle = PAPER_CARD
  ctx.fillRect(margin, contentTop, imgW, imgH)
  if (img) {
    ctx.drawImage(img, margin, contentTop, imgW, imgH)
  } else {
    ctx.fillStyle = INK_SOFT
    ctx.font = `400 20px ${serif}`
    ctx.textAlign = 'center'
    ctx.fillText('图片加载失败', margin + imgW / 2, contentTop + imgH / 2)
    ctx.textAlign = 'left'
  }
  ctx.strokeStyle = BORDER
  ctx.lineWidth = 1
  ctx.strokeRect(margin, contentTop, imgW, imgH)

  // 底部：二维码 + 文案
  const qrSize = 180
  const qrX = margin
  const qrY = bottomY + (bottomH - qrSize) / 2
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(qrX, qrY, qrSize, qrSize)
  const qrDataUrl = await QRCode.toDataURL(opts.shareUrl, {
    margin: 1,
    width: qrSize,
    color: { dark: INK, light: '#ffffff' },
  })
  const qrImg = await loadImage(qrDataUrl)
  ctx.drawImage(qrImg, qrX, qrY, qrSize, qrSize)

  const textX = qrX + qrSize + 28
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillStyle = INK
  ctx.font = `700 24px ${serif}`
  ctx.fillText('扫码访问本站', textX, qrY + 52)
  ctx.fillStyle = INK_SOFT
  ctx.font = `400 16px ${serif}`
  ctx.fillText(`查看这张作品 · ${safeHost(opts.shareUrl)}`, textX, qrY + 88)
  ctx.fillStyle = CINNABAR
  ctx.font = `400 14px ${serif}`
  ctx.fillText('PhotoStyle · 让每张照片都有风格', textX, qrY + 122)

  return canvas.toDataURL('image/png')
}

/** 由 dataURL 触发下载 */
export function downloadDataUrl(dataUrl: string, filename: string) {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
