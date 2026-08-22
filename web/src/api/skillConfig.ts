// 技能配置管理 API
import request from './request'

export interface SkillConfigItem {
  id: number
  skillId: string
  name: string
  description: string
  promptTemplate: string
  provider: string
  ratio: string
  subjectRatio: string
  category: string
  previewUrl: string | null
  isActive: boolean
  needAnalysis: boolean
  sortOrder: number
  createdAt: string
  updatedAt: string
}

export interface SkillConfigCreate {
  skillId: string
  name: string
  description?: string
  promptTemplate: string
  provider?: string
  ratio?: string
  subjectRatio?: string
  category?: string
  previewUrl?: string
  isActive?: boolean
  needAnalysis?: boolean
  sortOrder?: number
}

export interface SkillConfigUpdate {
  name?: string
  description?: string
  promptTemplate?: string
  provider?: string
  ratio?: string
  subjectRatio?: string
  category?: string
  previewUrl?: string
  isActive?: boolean
  needAnalysis?: boolean
  sortOrder?: number
}

/**
 * 获取所有技能配置列表
 */
export function getSkillConfigs() {
  return request<{ items: SkillConfigItem[]; total: number }>({
    url: '/admin/skills',
    method: 'get',
  })
}

/**
 * 获取单个技能配置详情
 */
export function getSkillConfig(skillId: string) {
  return request<SkillConfigItem>({
    url: `/admin/skills/${skillId}`,
    method: 'get',
  })
}

/**
 * 创建新技能配置
 */
export function createSkillConfig(data: SkillConfigCreate) {
  return request<SkillConfigItem>({
    url: '/admin/skills',
    method: 'post',
    data,
  })
}

/**
 * 更新技能配置
 */
export function updateSkillConfig(skillId: string, data: SkillConfigUpdate) {
  return request<SkillConfigItem>({
    url: `/admin/skills/${skillId}`,
    method: 'put',
    data,
  })
}

/**
 * 删除技能配置
 */
export function deleteSkillConfig(skillId: string) {
  return request({
    url: `/admin/skills/${skillId}`,
    method: 'delete',
  })
}

/**
 * 上传技能预览图
 */
export function uploadSkillPreview(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request<{ url: string }>({
    url: '/admin/skills/upload-preview',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}
