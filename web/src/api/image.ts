// 图片相关接口：上传、获取、删除
import { request } from './request'
import type { ImageInfo } from '@/types'

/**
 * 上传图片
 * @param file 图片文件
 * @param onProgress 上传进度回调（0-100）
 */
export function uploadImage(file: File, onProgress?: (percent: number) => void) {
  const formData = new FormData()
  formData.append('file', file)
  return request<ImageInfo>({
    url: '/images/upload',
    method: 'post',
    data: formData,
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
}

/**
 * 获取图片信息
 */
export function getImage(id: string) {
  return request<ImageInfo>({ url: `/images/${id}`, method: 'get' })
}

/**
 * 删除图片
 */
export function deleteImage(id: string) {
  return request<void>({ url: `/images/${id}`, method: 'delete' })
}
