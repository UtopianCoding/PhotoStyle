/**
 * 3D 翻页画册相关类型定义
 */

/** 画册页面数据 */
export interface FlipbookPage {
  id: string
  image?: string
  alt: string
  sourceFilename?: string
  width?: number
  height?: number
  caption?: string
  text?: string
  fit?: 'fill' | 'cover' | 'contain'
  padding?: number
  pageId?: string
  pageOrder?: number
  imageUrl?: string
  sourceImageId?: string
  imageWidth?: number | null
  imageHeight?: number | null
}

/** AI 生成的主题配置 */
export interface FlipbookTheme {
  mood?: string
  pageColor?: string
  coverColor?: string
  backCoverColor?: string
  pageTexture?: string
}

/** 画册项目 */
export interface FlipbookProject {
  projectId: string
  title: string
  kicker?: string
  status: 'creating' | 'analyzing' | 'ready' | 'error'
  coverUrl?: string | null
  themeJson?: string | FlipbookTheme | null
  pageCount: number
  pages: FlipbookPage[]
  createdAt: string
  updatedAt: string
  errorMessage?: string | null
}

/** 创建画册请求 */
export interface CreateFlipbookRequest {
  title: string
  resultIds: string[]
  kicker?: string
}

/** 画册布局参数 */
export interface BookLayout {
  width: number
  height: number
  minWidth: number
  minHeight: number
  maxWidth: number
  maxHeight: number
  defaultFit: 'fill' | 'contain'
  defaultPadding: number
}
