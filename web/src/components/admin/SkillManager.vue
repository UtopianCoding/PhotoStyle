<script setup lang="ts">
/**
 * 技能管理组件
 * 提供技能的增删改查功能，支持从数据库和文件系统加载技能
 */
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { request } from '@/api/request'

// 类型定义（与后端 camelCase 响应字段对齐）
interface SkillInputVariable {
  key: string
  label: string
  placeholder?: string
  hint?: string
  required?: boolean
  default?: string
  translate?: boolean
}
interface SkillConfigItem {
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
  previewUrls: string[]
  isActive: boolean
  needAnalysis: boolean
  inputVariables?: SkillInputVariable[]
  sortOrder: number
  createdAt: string
  updatedAt: string
}
interface SkillConfigCreate {
  skillId: string
  name: string
  description?: string
  promptTemplate: string
  provider?: string
  ratio?: string
  subjectRatio?: string
  category?: string
  previewUrl?: string
  previewUrls?: string[]
  isActive?: boolean
  needAnalysis?: boolean
  inputVariables?: SkillInputVariable[]
  sortOrder?: number
}
interface SkillConfigUpdate {
  name?: string
  description?: string
  promptTemplate?: string
  provider?: string
  ratio?: string
  subjectRatio?: string
  category?: string
  previewUrl?: string
  previewUrls?: string[]
  isActive?: boolean
  needAnalysis?: boolean
  inputVariables?: SkillInputVariable[]
  sortOrder?: number
}

// 技能列表
const skills = ref<SkillConfigItem[]>([])
const loading = ref(false)

// 编辑对话框
const editDialogVisible = ref(false)
const editingSkill = ref<SkillConfigItem | null>(null)
const isCreating = ref(false)

// 表单数据
const formData = ref<SkillConfigCreate & { id?: number }>({
  skillId: '',
  name: '',
  description: '',
  promptTemplate: '',
  provider: 'qianwen',
  ratio: '3:4',
  subjectRatio: '10-16%',
  category: '默认',
  previewUrl: '',
  previewUrls: [],
  isActive: true,
  needAnalysis: true,
  inputVariables: [],
  sortOrder: 100,
})

// 预览图上传
const previewUploading = ref(false)

// 表单验证规则
const formRules = {
  skillId: [{ required: true, message: '请输入技能ID', trigger: 'blur' }],
  name: [{ required: true, message: '请输入技能名称', trigger: 'blur' }],
  promptTemplate: [{ required: true, message: '请输入提示词模板', trigger: 'blur' }],
}

// 加载技能列表
async function loadSkills() {
  loading.value = true
  try {
    const res = await request<{ items: SkillConfigItem[]; total: number }>({
      url: '/admin/skills',
      method: 'get',
    })
    skills.value = res.items
  } catch (error) {
    ElMessage.error('加载技能列表失败')
  } finally {
    loading.value = false
  }
}

// 打开创建对话框
function openCreateDialog() {
  isCreating.value = true
  editingSkill.value = null
  formData.value = {
    skillId: '',
    name: '',
    description: '',
    promptTemplate: '',
    provider: 'qianwen',
    ratio: '3:4',
    subjectRatio: '10-16%',
    category: '默认',
    previewUrl: '',
    previewUrls: [],
    isActive: true,
    needAnalysis: true,
    inputVariables: [],
    sortOrder: 100,
  }
  editDialogVisible.value = true
}

// 打开编辑对话框
function openEditDialog(skill: SkillConfigItem) {
  isCreating.value = false
  editingSkill.value = skill
  formData.value = {
    id: skill.id,
    skillId: skill.skillId,
    name: skill.name,
    description: skill.description,
    promptTemplate: skill.promptTemplate,
    provider: skill.provider,
    ratio: skill.ratio,
    subjectRatio: skill.subjectRatio,
    category: skill.category,
    previewUrl: skill.previewUrl || (skill.previewUrls && skill.previewUrls.length > 0 ? skill.previewUrls[0] : ''),
    previewUrls: skill.previewUrls || (skill.previewUrl ? [skill.previewUrl] : []),
    isActive: skill.isActive,
    needAnalysis: skill.needAnalysis,
    inputVariables: skill.inputVariables?.map((v) => ({ ...v })) || [],
    sortOrder: skill.sortOrder,
  }
  editDialogVisible.value = true
}

// 关闭对话框
function closeDialog() {
  editDialogVisible.value = false
  editingSkill.value = null
}

// 保存技能
async function saveSkill() {
  if (!formData.value.skillId || !formData.value.name || !formData.value.promptTemplate) {
    ElMessage.warning('请填写必填字段')
    return
  }

  try {
    if (isCreating.value) {
      const createData: SkillConfigCreate = { ...formData.value }
    await request({
      url: '/admin/skills',
      method: 'post',
      data: createData,
    })
      ElMessage.success('创建成功')
    } else if (editingSkill.value) {
      const updateData: SkillConfigUpdate = {
        name: formData.value.name,
        description: formData.value.description,
        promptTemplate: formData.value.promptTemplate,
        provider: formData.value.provider,
        ratio: formData.value.ratio,
        subjectRatio: formData.value.subjectRatio,
        category: formData.value.category,
        previewUrl: formData.value.previewUrl,
        previewUrls: formData.value.previewUrls,
        isActive: formData.value.isActive,
        needAnalysis: formData.value.needAnalysis,
        inputVariables: formData.value.inputVariables,
        sortOrder: formData.value.sortOrder,
      }
      await request({
        url: `/admin/skills/${editingSkill.value.skillId}`,
        method: 'put',
        data: updateData,
      })
      ElMessage.success('更新成功')
    }
    closeDialog()
    await loadSkills()
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  }
}

// 删除技能
async function handleDelete(skill: SkillConfigItem) {
  try {
    await ElMessageBox.confirm(
      `确定要删除技能 "${skill.name}" 吗？此操作不可撤销。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await request({
      url: `/admin/skills/${skill.skillId}`,
      method: 'delete',
    })
    ElMessage.success('删除成功')
    await loadSkills()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 切换启用状态
async function toggleActive(skill: SkillConfigItem) {
  try {
    await request({
      url: `/admin/skills/${skill.skillId}`,
      method: 'put',
      data: { isActive: !skill.isActive },
    })
    ElMessage.success(skill.isActive ? '已禁用' : '已启用')
    await loadSkills()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 上传预览图
async function handlePreviewUpload(options: any) {
  const file = options.file
  if (!file) return

  previewUploading.value = true
  try {
    const uploadFormData = new FormData()
    uploadFormData.append('file', file)
    const res = await request<{ url: string }>({
      url: '/admin/skills/upload-preview',
      method: 'post',
      data: uploadFormData,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    // 添加到 previewUrls 数组
    if (!formData.value.previewUrls) {
      formData.value.previewUrls = []
    }
    formData.value.previewUrls.push(res.url)
    // 同时更新 previewUrl 为第一张图
    if (formData.value.previewUrls.length === 1) {
      formData.value.previewUrl = res.url
    }
    ElMessage.success('预览图上传成功')
  } catch (error) {
    ElMessage.error('上传失败')
  } finally {
    previewUploading.value = false
  }
}

// 移除预览图
function removePreview(index: number) {
  if (!formData.value.previewUrls) return
  formData.value.previewUrls.splice(index, 1)
  // 更新 previewUrl
  if (formData.value.previewUrls.length > 0) {
    formData.value.previewUrl = formData.value.previewUrls[0]
  } else {
    formData.value.previewUrl = ''
  }
}

// 添加输入变量
function addInputVariable() {
  if (!formData.value.inputVariables) {
    formData.value.inputVariables = []
  }
  formData.value.inputVariables.push({
    key: '',
    label: '',
    placeholder: '',
    hint: '',
    required: false,
    default: '',
    translate: false,
  })
}

// 移除输入变量
function removeInputVariable(index: number) {
  formData.value.inputVariables?.splice(index, 1)
}

// 获取状态标签类型
function getStatusType(isActive: boolean) {
  return isActive ? 'success' : 'info'
}

// 获取状态文本
function getStatusText(isActive: boolean) {
  return isActive ? '启用' : '禁用'
}

// 初始化
onMounted(() => {
  loadSkills()
})
</script>

<template>
  <div class="skill-manager">
    <!-- 操作栏 -->
    <div class="skill-manager__header">
      <h2 class="skill-manager__title font-display">技能管理</h2>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新建技能
      </el-button>
    </div>

    <!-- 技能列表 -->
    <el-table :data="skills" v-loading="loading" stripe class="skill-manager__table">
      <el-table-column prop="skillId" label="技能ID" min-width="160" />
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="category" label="分类" min-width="80" />
      <el-table-column prop="provider" label="提供商" min-width="90" />
      <el-table-column prop="ratio" label="比例" width="70" />
      <el-table-column label="状态" width="70">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.isActive)" size="small">
            {{ getStatusText(row.isActive) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分析" width="60">
        <template #default="{ row }">
          <el-tag :type="row.needAnalysis ? 'success' : 'info'" size="small">
            {{ row.needAnalysis ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sortOrder" label="排序" width="60" />
      <el-table-column label="预览图" width="80">
        <template #default="{ row }">
          <el-image
            v-if="row.previewUrl || (row.previewUrls && row.previewUrls.length > 0)"
            :src="row.previewUrl || row.previewUrls[0]"
            fit="cover"
            style="width: 56px; height: 56px; border-radius: 4px"
            :preview-src-list="row.previewUrls && row.previewUrls.length > 0 ? row.previewUrls : [row.previewUrl]"
            preview-teleported
          />
          <span v-else class="text-gray-400">无</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEditDialog(row as SkillConfigItem)">
            编辑
          </el-button>
          <el-button link :type="(row as SkillConfigItem).isActive ? 'warning' : 'success'" @click="toggleActive(row as SkillConfigItem)">
            {{ (row as SkillConfigItem).isActive ? '禁用' : '启用' }}
          </el-button>
          <el-button link type="danger" @click="handleDelete(row as SkillConfigItem)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      :title="isCreating ? '新建技能' : '编辑技能'"
      width="900px"
      @close="closeDialog"
    >
      <el-form :model="formData" :rules="formRules" label-width="120px">
        <el-form-item label="技能ID" prop="skillId">
          <el-input
            v-model="formData.skillId"
            :disabled="!isCreating"
            placeholder="例如: photo-revival"
          />
        </el-form-item>
        <el-form-item label="技能名称" prop="name">
          <el-input v-model="formData.name" placeholder="例如: 老照片复兴" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="2"
            placeholder="技能描述"
          />
        </el-form-item>
        <el-form-item label="提示词模板" prop="promptTemplate">
          <el-input
            v-model="formData.promptTemplate"
            type="textarea"
            :rows="8"
            placeholder="输入提示词模板"
          />
        </el-form-item>
        <el-form-item label="提供商">
          <el-select v-model="formData.provider" style="width: 100%">
            <el-option label="千问 (Qianwen)" value="qianwen" />
            <el-option label="OpenAI" value="openai" />
            <el-option label="Claude" value="claude" />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="比例">
              <el-input v-model="formData.ratio" placeholder="例如: 3:4" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="主体占比">
              <el-input v-model="formData.subjectRatio" placeholder="例如: 10-16%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="分类">
          <el-input v-model="formData.category" placeholder="例如: 默认" />
        </el-form-item>
        <el-form-item label="预览图">
          <div class="skill-manager__preview-list">
            <div
              v-for="(url, index) in formData.previewUrls || []"
              :key="index"
              class="skill-manager__preview-item"
            >
              <el-image
                :src="url"
                fit="cover"
                style="width: 100px; height: 100px; border-radius: 8px"
                :preview-src-list="formData.previewUrls || []"
                :initial-index="index"
                preview-teleported
              />
              <el-button
                type="danger"
                size="small"
                circle
                class="skill-manager__preview-remove"
                @click="removePreview(index)"
              >
                ×
              </el-button>
            </div>
            <el-upload
              :show-file-list="false"
              :http-request="handlePreviewUpload"
              accept="image/*"
              class="skill-manager__preview-upload-btn"
            >
              <el-button :loading="previewUploading">
                <el-icon><Plus /></el-icon>
                添加预览图
              </el-button>
            </el-upload>
          </div>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="启用状态">
              <el-switch v-model="formData.isActive" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="需要分析">
              <el-switch v-model="formData.needAnalysis" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="输入变量">
          <div class="skill-manager__iv-list">
            <div
              v-for="(iv, index) in formData.inputVariables || []"
              :key="index"
              class="skill-manager__iv-item"
            >
              <div class="skill-manager__iv-row">
                <el-input
                  v-model="iv.key"
                  placeholder="变量key（如 location）"
                  style="width: 160px"
                />
                <el-input
                  v-model="iv.label"
                  placeholder="标签（如 拍摄地点）"
                  style="width: 140px"
                />
                <el-input
                  v-model="iv.placeholder"
                  placeholder="占位提示"
                  style="width: 180px"
                />
                <el-button
                  type="danger"
                  size="small"
                  circle
                  @click="removeInputVariable(index)"
                >
                  ×
                </el-button>
              </div>
              <div class="skill-manager__iv-row">
                <el-input
                  v-model="iv.hint"
                  placeholder="辅助提示（如：将自动翻译为英文）"
                  style="width: 280px"
                />
                <el-input
                  v-model="iv.default"
                  placeholder="默认值（留空则未填写时替换为空）"
                  style="width: 240px"
                />
                <el-checkbox v-model="iv.required">必填</el-checkbox>
                <el-checkbox v-model="iv.translate">需翻译</el-checkbox>
              </div>
            </div>
            <el-button size="small" @click="addInputVariable">
              <el-icon><Plus /></el-icon>
              添加变量
            </el-button>
            <span class="skill-manager__hint">
              提示词模板中写 {{key}} 占位符，前端据此渲染输入框
            </span>
          </div>
        </el-form-item>
        <el-form-item label="排序权重">
          <el-input-number
            v-model="formData.sortOrder"
            :min="0"
            :max="1000"
            controls-position="right"
          />
          <span class="skill-manager__hint">数字越小越靠前</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="saveSkill">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.skill-manager {
  padding: 24px;
}

.skill-manager__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.skill-manager__title {
  margin: 0;
  font-size: 24px;
  color: var(--el-text-color-primary);
}

.skill-manager__table {
  width: 100%;
}

.skill-manager__preview-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-start;
}

.skill-manager__preview-item {
  position: relative;
  display: inline-block;
}

.skill-manager__preview-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 20px;
  height: 20px;
  padding: 0;
  font-size: 14px;
  line-height: 1;
}

.skill-manager__preview-upload-btn {
  display: inline-block;
  vertical-align: top;
}

.skill-manager__hint {
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.skill-manager__iv-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.skill-manager__iv-item {
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.skill-manager__iv-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
