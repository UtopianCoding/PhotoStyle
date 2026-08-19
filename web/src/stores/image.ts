// 图片状态管理：当前上传的图片信息与上传进度
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ImageInfo } from '@/types'
import { listImages } from '@/api/image'

export const useImageStore = defineStore('image', () => {
  // 图片 ID
  const imageId = ref<string>('')
  // 原图 URL
  const originalUrl = ref<string>('')
  // 缩略图 URL
  const thumbnailUrl = ref<string>('')
  // 上传进度（0-100）
  const uploadProgress = ref<number>(0)

  // 当前用户已上传图片列表（用于「选择已上传图片」）
  const myImages = ref<ImageInfo[]>([])
  // 列表加载中
  const myImagesLoading = ref<boolean>(false)
  // 列表是否已加载过（避免重复请求）
  const myImagesLoaded = ref<boolean>(false)

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

  /** 加载当前用户已上传图片列表（仅首次加载） */
  async function loadMyImages() {
    if (myImagesLoaded.value || myImagesLoading.value) return
    myImagesLoading.value = true
    try {
      myImages.value = await listImages()
      myImagesLoaded.value = true
    } catch {
      // 加载失败保持为空，不影响上传主流程
    } finally {
      myImagesLoading.value = false
    }
  }

  /** 重置图片状态 */
  function reset() {
    imageId.value = ''
    originalUrl.value = ''
    thumbnailUrl.value = ''
    uploadProgress.value = 0
  }

  return {
    imageId,
    originalUrl,
    thumbnailUrl,
    uploadProgress,
    myImages,
    myImagesLoading,
    myImagesLoaded,
    setImage,
    setProgress,
    loadMyImages,
    reset,
  }
})
