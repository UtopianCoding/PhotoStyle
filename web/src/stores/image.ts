// 图片状态管理：当前上传的图片信息与上传进度
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ImageInfo } from '@/types'

export const useImageStore = defineStore('image', () => {
  // 图片 ID
  const imageId = ref<string>('')
  // 原图 URL
  const originalUrl = ref<string>('')
  // 缩略图 URL
  const thumbnailUrl = ref<string>('')
  // 上传进度（0-100）
  const uploadProgress = ref<number>(0)

  /** 设置当前图片 */
  function setImage(image: ImageInfo) {
    imageId.value = image.imageId
    originalUrl.value = image.originalUrl
    thumbnailUrl.value = image.thumbnailUrl || ''
    uploadProgress.value = 100
  }

  /** 更新上传进度 */
  function setProgress(percent: number) {
    uploadProgress.value = percent
  }

  /** 重置图片状态 */
  function reset() {
    imageId.value = ''
    originalUrl.value = ''
    thumbnailUrl.value = ''
    uploadProgress.value = 0
  }

  return { imageId, originalUrl, thumbnailUrl, uploadProgress, setImage, setProgress, reset }
})
