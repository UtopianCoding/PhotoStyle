// 上传逻辑组合式函数：处理图片校验、压缩预览与上传进度
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadImage as uploadImageApi } from '@/api/image'
import { useImageStore } from '@/stores/image'
import { compressImage, isImageFile } from '@/utils/image'
import type { ImageInfo } from '@/types'

export function useUpload() {
  // 是否上传中
  const uploading = ref(false)
  // 上传进度（0-100）
  const progress = ref(0)
  // 本地预览地址
  const previewUrl = ref('')
  const imageStore = useImageStore()

  /**
   * 上传图片
   * @returns 上传成功后的图片信息，失败返回 null
   */
  async function upload(file: File): Promise<ImageInfo | null> {
    if (!isImageFile(file)) {
      ElMessage.warning('请选择图片文件')
      return null
    }
    uploading.value = true
    progress.value = 0
    try {
      // 生成本地压缩预览
      previewUrl.value = await compressImage(file, 1024, 0.7).catch(() => URL.createObjectURL(file))
      imageStore.setProgress(0)
      const image = await uploadImageApi(file, (p) => {
        progress.value = p
        imageStore.setProgress(p)
      })
      imageStore.setImage(image)
      ElMessage.success('上传成功')
      return image
    } catch {
      ElMessage.error('上传失败')
      return null
    } finally {
      uploading.value = false
    }
  }

  /** 重置上传状态 */
  function reset() {
    uploading.value = false
    progress.value = 0
    previewUrl.value = ''
  }

  return { uploading, progress, previewUrl, upload, reset }
}
