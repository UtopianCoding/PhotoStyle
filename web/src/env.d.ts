/// <reference types="vite/client" />

// page-flip 库类型声明
declare module 'page-flip' {
  export interface FlipSetting {
    width?: number
    height?: number
    size?: 'fixed' | 'stretch'
    minWidth?: number
    maxWidth?: number
    minHeight?: number
    maxHeight?: number
    startPage?: number
    drawShadow?: boolean
    flippingTime?: number
    usePortrait?: boolean
    startZIndex?: number
    autoSize?: boolean
    maxShadowOpacity?: number
    showCover?: boolean
    mobileScrollSupport?: boolean
    clickEventForward?: boolean
    useMouseEvents?: boolean
    swipeDistance?: number
    showPageCorners?: boolean
    disableFlipByClick?: boolean
  }

  export interface FlipEvent {
    data: number | string
    object: unknown
  }

  export class PageFlip {
    constructor(element: HTMLElement, settings: FlipSetting)
    loadFromHTML(elements: NodeListOf<HTMLElement> | HTMLElement[]): void
    flip(page: number, corner?: 'top' | 'bottom'): void
    flipNext(corner?: 'top' | 'bottom'): void
    flipPrev(corner?: 'top' | 'bottom'): void
    getCurrentPageIndex(): number
    getPageCount(): number
    on(eventName: string, callback: (e: FlipEvent) => void): void
    off(eventName: string, callback: (e: FlipEvent) => void): void
    destroy(): void
  }
}

// .vue 单文件组件的类型声明
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: DefineComponent<Record<string, never>, Record<string, never>, unknown>
  export default component
}

// 环境变量类型声明
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_APP_TITLE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
