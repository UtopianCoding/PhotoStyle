<script setup lang="ts">
// 后台配置页：模型 / 存储 / 应用 三个分区表单，写入 .env 后需重启后端生效
// 用户管理：查看用户、分配权限、编辑资料（仅拥有 admin:users 权限可见）
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import * as adminApi from '@/api/admin'
import { getPermissionCatalog, updateUser, uploadAvatar } from '@/api/user'
import { useUserStore } from '@/stores/user'
import SkillManager from '@/components/admin/SkillManager.vue'
import FeedbackManager from '@/components/admin/FeedbackManager.vue'
import type {
  AdminUserItem,
  PermissionCatalog,
  SystemConfig,
  SystemConfigUpdate,
} from '@/types'

const userStore = useUserStore()
const canManageUsers = computed(() => userStore.hasPermission('admin:users'))

// ===================== 系统配置 =====================
// 表单引用
const formRef = ref<FormInstance>()
// 加载/保存中
const loading = ref(false)
const saving = ref(false)
// 模型 provider 当前激活的 tab（使用 provider_id：qianwen / dalle / minimax / volcengine）
const activeProviderTab = ref<'qianwen' | 'dalle' | 'minimax' | 'volcengine'>('qianwen')

// 表单数据：直接对齐后端字段，CORS 来源用逗号分隔字符串维护
const form = reactive({
  model: {
    defaultProvider: 'qianwen',
    enabledProviders: ['qianwen'] as string[],
    qianwen: {
      apiKey: '',
      modelVision: '',
      modelImage: '',
      workspaceId: '',
      region: '',
      watermark: false as boolean,
      width: null as number | null,
      height: null as number | null,
      seed: null as number | null,
      timeout: null as number | null,
      promptExtend: false as boolean,
    },
    dalle: {
      apiKey: '',
      baseUrl: '',
      modelImage: '',
    },
    minimax: {
      apiKey: '',
      baseUrl: '',
      modelImage: '',
      watermark: false as boolean,
      width: null as number | null,
      height: null as number | null,
      seed: null as number | null,
    },
    volcengine: {
      apiKey: '',
      baseUrl: '',
      modelImage: '',
      watermark: false as boolean,
      width: null as number | null,
      height: null as number | null,
      seed: null as number | null,
    },
  },
  storage: {
    storageType: 'minio',
    minio: {
      endpoint: '',
      accessKey: '',
      secretKey: '',
      bucket: '',
      secure: false,
      publicBaseUrl: '',
    },
    oss: {
      accessKeyId: '',
      accessKeySecret: '',
      bucket: '',
      endpoint: '',
    },
  },
  app: {
    logLevel: 'INFO',
    corsAllowedOrigins: '',
    rateLimitCreditCostPerConvert: 4,
    accessTokenExpireMinutes: 120,
  },
})

// 日志级别可选项
const logLevelOptions = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
// 存储类型可选项
const storageTypeOptions = [
  { label: 'MinIO', value: 'minio' },
  { label: '阿里云 OSS', value: 'oss' },
]
// 默认 provider 可选项（value 为 provider_id，与后端 ProviderManager 一致）
const providerOptions = [
  { label: '千问 (DashScope)', value: 'qianwen' },
  { label: 'OpenAI (DALL-E)', value: 'dalle' },
  { label: 'MiniMax', value: 'minimax' },
  { label: '火山引擎 (Seedream)', value: 'volcengine' },
]

/** 加载当前系统配置 */
async function loadConfig() {
  loading.value = true
  try {
    const data: SystemConfig = await adminApi.getSystemConfig()
    fillForm(data)
    // 默认激活 tab 跟随 defaultProvider
    const dp = data.model.defaultProvider
    if (dp === 'dalle' || dp === 'minimax' || dp === 'qianwen' || dp === 'volcengine') {
      activeProviderTab.value = dp
    }
  } catch {
    // request 拦截器已提示错误
  } finally {
    loading.value = false
  }
}

/** 将后端返回的配置填充到表单 */
function fillForm(data: SystemConfig) {
  form.model.defaultProvider = data.model.defaultProvider
  form.model.enabledProviders = data.model.enabledProviders?.length
    ? [...data.model.enabledProviders]
    : ['qianwen']
  // 千问配置：处理可能的 null 值
  const qw = data.model.qianwen
  form.model.qianwen = {
    apiKey: qw.apiKey,
    modelVision: qw.modelVision,
    modelImage: qw.modelImage,
    workspaceId: qw.workspaceId,
    region: qw.region,
    watermark: qw.watermark ?? false,
    width: qw.width,
    height: qw.height,
    seed: qw.seed,
    timeout: qw.timeout ?? null,
    promptExtend: qw.promptExtend ?? true,
  }
  form.model.dalle = { ...data.model.dalle }
  // MiniMax 配置：处理可能的 null 值
  const mm = data.model.minimax
  form.model.minimax = {
    apiKey: mm.apiKey,
    baseUrl: mm.baseUrl,
    modelImage: mm.modelImage,
    watermark: mm.watermark ?? false,
    width: mm.width,
    height: mm.height,
    seed: mm.seed,
  }
  // 火山引擎配置：处理可能的 null 值
  const vc = data.model.volcengine
  form.model.volcengine = {
    apiKey: vc.apiKey,
    baseUrl: vc.baseUrl,
    modelImage: vc.modelImage,
    watermark: vc.watermark ?? false,
    width: vc.width,
    height: vc.height,
    seed: vc.seed,
  }

  form.storage.storageType = data.storage.storageType
  form.storage.minio = { ...data.storage.minio }
  form.storage.oss = { ...data.storage.oss }

  form.app.logLevel = data.app.logLevel
  form.app.corsAllowedOrigins = data.app.corsAllowedOrigins.join(', ')
  form.app.rateLimitCreditCostPerConvert = data.app.rateLimitCreditCostPerConvert
  form.app.accessTokenExpireMinutes = data.app.accessTokenExpireMinutes
}

/** 构造更新 payload：敏感字段若仍为脱敏形态则跳过，避免覆盖为脏值 */
function buildPayload(): SystemConfigUpdate {
  const payload: SystemConfigUpdate = {}

  // 模型配置
  const model: NonNullable<SystemConfigUpdate['model']> = {
    defaultProvider: form.model.defaultProvider,
    enabledProviders: [...form.model.enabledProviders],
  }
  // 千问
  const ds = form.model.qianwen
  const qianwen: NonNullable<NonNullable<SystemConfigUpdate['model']>['qianwen']> = {}
  if (ds.apiKey && !ds.apiKey.includes('****')) qianwen.apiKey = ds.apiKey
  if (ds.modelVision) qianwen.modelVision = ds.modelVision
  if (ds.modelImage) qianwen.modelImage = ds.modelImage
  qianwen.workspaceId = ds.workspaceId
  if (ds.region) qianwen.region = ds.region
  qianwen.watermark = ds.watermark
  qianwen.width = ds.width
  qianwen.height = ds.height
  qianwen.seed = ds.seed
  // timeout：空输入框（null）→ 0，后端将 0 视为"删除字段，恢复默认 300"
  qianwen.timeout = ds.timeout ?? 0
  // promptExtend：始终发送 true/false，后端视为"覆盖写入"
  qianwen.promptExtend = ds.promptExtend ?? true
  if (Object.keys(qianwen).length > 0) model.qianwen = qianwen
  // OpenAI / DALL-E
  const op = form.model.dalle
  const dalle: NonNullable<NonNullable<SystemConfigUpdate['model']>['dalle']> = {}
  if (op.apiKey && !op.apiKey.includes('****')) dalle.apiKey = op.apiKey
  if (op.baseUrl) dalle.baseUrl = op.baseUrl
  if (op.modelImage) dalle.modelImage = op.modelImage
  if (Object.keys(dalle).length > 0) model.dalle = dalle
  // MiniMax
  const mm = form.model.minimax
  const minimax: NonNullable<NonNullable<SystemConfigUpdate['model']>['minimax']> = {}
  if (mm.apiKey && !mm.apiKey.includes('****')) minimax.apiKey = mm.apiKey
  if (mm.baseUrl) minimax.baseUrl = mm.baseUrl
  if (mm.modelImage) minimax.modelImage = mm.modelImage
  minimax.watermark = mm.watermark
  minimax.width = mm.width
  minimax.height = mm.height
  minimax.seed = mm.seed
  if (Object.keys(minimax).length > 0) model.minimax = minimax
  // 火山引擎（Seedream）
  const vc = form.model.volcengine
  const volcengine: NonNullable<NonNullable<SystemConfigUpdate['model']>['volcengine']> = {}
  if (vc.apiKey && !vc.apiKey.includes('****')) volcengine.apiKey = vc.apiKey
  if (vc.baseUrl) volcengine.baseUrl = vc.baseUrl
  if (vc.modelImage) volcengine.modelImage = vc.modelImage
  volcengine.watermark = vc.watermark
  volcengine.width = vc.width
  volcengine.height = vc.height
  volcengine.seed = vc.seed
  if (Object.keys(volcengine).length > 0) model.volcengine = volcengine
  payload.model = model

  // 存储配置
  const storage: NonNullable<SystemConfigUpdate['storage']> = {
    storageType: form.storage.storageType,
  }
  // MinIO（始终发送，敏感字段跳过逻辑保护）
  const mn = form.storage.minio
  const minio: NonNullable<NonNullable<SystemConfigUpdate['storage']>['minio']> = {}
  if (mn.endpoint) minio.endpoint = mn.endpoint
  if (mn.accessKey && !mn.accessKey.includes('****')) minio.accessKey = mn.accessKey
  if (mn.secretKey && !mn.secretKey.includes('****')) minio.secretKey = mn.secretKey
  if (mn.bucket) minio.bucket = mn.bucket
  minio.secure = mn.secure
  if (mn.publicBaseUrl) minio.publicBaseUrl = mn.publicBaseUrl
  if (Object.keys(minio).length > 0) storage.minio = minio
  // OSS
  const osCfg = form.storage.oss
  const oss: NonNullable<NonNullable<SystemConfigUpdate['storage']>['oss']> = {}
  if (osCfg.accessKeyId && !osCfg.accessKeyId.includes('****')) oss.accessKeyId = osCfg.accessKeyId
  if (osCfg.accessKeySecret && !osCfg.accessKeySecret.includes('****')) {
    oss.accessKeySecret = osCfg.accessKeySecret
  }
  if (osCfg.bucket) oss.bucket = osCfg.bucket
  if (osCfg.endpoint) oss.endpoint = osCfg.endpoint
  if (Object.keys(oss).length > 0) storage.oss = oss
  payload.storage = storage

  // 应用配置
  const app: NonNullable<SystemConfigUpdate['app']> = {}
  if (form.app.logLevel) app.logLevel = form.app.logLevel
  const origins = form.app.corsAllowedOrigins
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  if (origins.length > 0) app.corsAllowedOrigins = origins
  app.rateLimitCreditCostPerConvert = form.app.rateLimitCreditCostPerConvert
  app.accessTokenExpireMinutes = form.app.accessTokenExpireMinutes
  if (Object.keys(app).length > 0) payload.app = app

  return payload
}

/** 保存配置 */
async function onSave() {
  if (!formRef.value) return
  saving.value = true
  try {
    const payload = buildPayload()
    const data = await adminApi.updateSystemConfig(payload)
    fillForm(data)
    ElMessage.success('模型配置已立即生效，存储/应用配置需重启后端服务')
  } catch {
    // request 拦截器已提示错误
  } finally {
    saving.value = false
  }
}

/** 重新加载（放弃未保存修改） */
async function onReset() {
  await loadConfig()
  ElMessage.info('已重新加载当前配置')
}

// ===================== 用户管理 =====================
const activeTab = ref<'config' | 'users' | 'skills' | 'feedbacks'>('config')

const users = ref<AdminUserItem[]>([])
const userTotal = ref(0)
const userPage = ref(1)
const userPageSize = ref(10)
const usersLoading = ref(false)
const catalog = ref<PermissionCatalog | null>(null)

// 编辑弹窗
const editVisible = ref(false)
const editing = ref<AdminUserItem | null>(null)
const editForm = reactive({
  nickname: '',
  avatarUrl: '' as string,
  status: 'active',
  isAdmin: false,
  permissions: [] as string[],
})
const avatarPreview = ref('')
const editUploading = ref(false)
const savingUser = ref(false)
const editFileInput = ref<HTMLInputElement | null>(null)
const rolePresetKey = ref<string>('')

/** 加载权限目录 */
async function loadCatalog() {
  try {
    catalog.value = await getPermissionCatalog()
  } catch {
    // 拦截器已提示
  }
}

/** 加载用户列表 */
async function loadUsers() {
  usersLoading.value = true
  try {
    const data = await adminApi.listUsers({ page: userPage.value, pageSize: userPageSize.value })
    users.value = data.items
    userTotal.value = data.total
  } catch {
    // 拦截器已提示
  } finally {
    usersLoading.value = false
  }
}

/** 分页变化 */
function onUserPageChange(page: number) {
  userPage.value = page
  loadUsers()
}

/** 打开编辑弹窗 */
function openEdit(row: AdminUserItem) {
  editing.value = row
  editForm.nickname = row.nickname ?? ''
  editForm.avatarUrl = row.avatarUrl ?? ''
  editForm.status = row.status
  editForm.isAdmin = row.isAdmin
  editForm.permissions = [...row.permissions]
  avatarPreview.value = row.avatarUrl ?? ''
  rolePresetKey.value = ''
  editVisible.value = true
}

/** 触发头像文件选择 */
function triggerEditUpload() {
  editFileInput.value?.click()
}

/** 上传头像 */
async function onEditFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    target.value = ''
    return
  }
  editUploading.value = true
  try {
    const res = await uploadAvatar(file)
    editForm.avatarUrl = res.avatarUrl
    avatarPreview.value = res.avatarUrl
    ElMessage.success('头像已上传，点击保存生效')
  } catch {
    // 拦截器已提示
  } finally {
    editUploading.value = false
    target.value = ''
  }
}

/** 应用角色预设：快速填充权限与管理员标记 */
function applyRolePreset(key: string) {
  const preset = catalog.value?.rolePresets.find((p) => p.key === key)
  if (!preset) return
  editForm.permissions = [...preset.permissions]
  editForm.isAdmin = preset.isAdmin
  ElMessage.info(`已套用角色「${preset.label}」的权限`)
}

/** 保存用户编辑 */
async function onSaveUser() {
  if (!editing.value) return
  savingUser.value = true
  try {
    const updated = await updateUser(editing.value.userId, {
      nickname: editForm.nickname,
      avatarUrl: editForm.avatarUrl || null,
      status: editForm.status,
      isAdmin: editForm.isAdmin,
      permissions: editForm.permissions,
    })
    ElMessage.success('用户已更新')
    editVisible.value = false
    // 若编辑的是当前登录用户，同步本地权限
    if (updated.userId === userStore.userId) {
      userStore.updateLocalProfile({
        nickname: updated.nickname ?? '',
        avatarUrl: updated.avatarUrl ?? '',
        isAdmin: updated.isAdmin,
        permissions: updated.permissions,
      })
    }
    await loadUsers()
  } catch {
    // 拦截器已提示
  } finally {
    savingUser.value = false
  }
}

/** 切换到用户管理页时加载数据 */
function onTabChange(tab: string | number) {
  if (tab === 'users' && canManageUsers.value) {
    loadCatalog()
    loadUsers()
  }
}

onMounted(() => {
  loadConfig()
  if (canManageUsers.value) {
    loadCatalog()
    loadUsers()
  }
})
</script>

<template>
  <div v-loading="loading" class="admin-page mx-auto max-w-7xl px-6 py-10">
    <!-- 标题区 -->
    <section class="hero ink-fade">
      <div class="hero__seal-wrap">
        <span class="hero__seal">管</span>
      </div>
      <h1 class="hero__title font-display">后台管理</h1>
      <p class="hero__subtitle">管理模型参数、用户权限与应用配置</p>
    </section>

    <el-tabs v-model="activeTab" class="admin-tabs" @tab-change="onTabChange">
      <!-- 系统配置 -->
      <el-tab-pane label="系统配置" name="config">
        <el-form ref="formRef" :model="form" label-position="top" class="admin-form">
          <!-- 模型配置 -->
          <section class="notebook-section ink-fade">
            <h2 class="notebook-section__label font-display">
              <span class="ink-stamp">壹</span>
              <span>模型配置</span>
            </h2>

            <el-form-item label="默认模型服务方" class="default-provider-item">
              <el-select v-model="form.model.defaultProvider" class="w-full">
                <el-option
                  v-for="opt in providerOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
              <div class="field-hint">选择图像生成默认使用的 Provider，可下方分别配置多个</div>
            </el-form-item>

            <el-form-item label="启用模型（多选）" class="enabled-providers-item">
              <el-checkbox-group v-model="form.model.enabledProviders">
                <el-checkbox
                  v-for="opt in providerOptions"
                  :key="opt.value"
                  :label="opt.value"
                >
                  {{ opt.label }}
                </el-checkbox>
              </el-checkbox-group>
              <div class="field-hint">勾选后用户每次转换将同时调用这些模型，积分只扣一次</div>
            </el-form-item>

            <el-tabs v-model="activeProviderTab" class="provider-tabs">
              <el-tab-pane label="千问 (DashScope)" name="qianwen">
                <div class="form-grid">
                  <el-form-item label="API Key">
                    <el-input
                      v-model="form.model.qianwen.apiKey"
                      placeholder="脱敏显示，如需修改请清空后输入新值"
                      show-password
                    />
                    <div class="field-hint">敏感字段，保存时若仍含 **** 将跳过写入</div>
                  </el-form-item>
                  <el-form-item label="视觉理解模型">
                    <el-input v-model="form.model.qianwen.modelVision" placeholder="如 qwen-vl-plus" />
                  </el-form-item>
                  <el-form-item label="图像生成模型">
                    <el-input v-model="form.model.qianwen.modelImage" placeholder="如 qwen-image-3.0-pro" />
                  </el-form-item>
                  <el-form-item label="工作空间 ID">
                    <el-input
                      v-model="form.model.qianwen.workspaceId"
                      placeholder="留空使用共享 DashScope 端点"
                    />
                  </el-form-item>
                  <el-form-item label="区域">
                    <el-input v-model="form.model.qianwen.region" placeholder="如 cn-beijing" />
                  </el-form-item>
                  <el-form-item label="AI 水印">
                    <el-switch v-model="form.model.qianwen.watermark" :active-value="true" :inactive-value="false" active-text="开启" inactive-text="关闭" />
                    <div class="field-hint">开启后将在生成图片上添加水印，留空则不设置</div>
                  </el-form-item>
                  <el-form-item label="图片宽度（像素）">
                    <el-input-number v-model="form.model.qianwen.width" :min="512" :max="2048" :step="8" controls-position="right" placeholder="留空不设置" />
                  </el-form-item>
                  <el-form-item label="图片高度（像素）">
                    <el-input-number v-model="form.model.qianwen.height" :min="512" :max="2048" :step="8" controls-position="right" placeholder="留空不设置" />
                  </el-form-item>
                  <el-form-item label="随机数种子">
                    <el-input-number v-model="form.model.qianwen.seed" :min="0" :max="2147483647" controls-position="right" placeholder="留空使用随机种子" />
                    <div class="field-hint">固定种子可使生成结果相对稳定</div>
                  </el-form-item>
                  <el-form-item label="请求超时（秒）">
                    <el-input-number v-model="form.model.qianwen.timeout" :min="30" :max="1800" :step="30" controls-position="right" placeholder="默认 300" />
                    <div class="field-hint">单次调用千问模型的最大等待时间（30~1800 秒），留空则使用默认 300 秒</div>
                  </el-form-item>
                  <el-form-item label="提示词自动扩展">
                    <el-switch v-model="form.model.qianwen.promptExtend" :active-value="true" :inactive-value="false" active-text="开启" inactive-text="关闭" />
                    <div class="field-hint">启用后千问会自动优化提示词（长提示词建议关闭以避免超时）</div>
                  </el-form-item>
                </div>
              </el-tab-pane>

              <el-tab-pane label="OpenAI (DALL-E)" name="dalle">
                <div class="form-grid">
                  <el-form-item label="API Key">
                    <el-input
                      v-model="form.model.dalle.apiKey"
                      placeholder="脱敏显示，如需修改请清空后输入新值"
                      show-password
                    />
                    <div class="field-hint">敏感字段，保存时若仍含 **** 将跳过写入</div>
                  </el-form-item>
                  <el-form-item label="接口基础地址">
                    <el-input v-model="form.model.dalle.baseUrl" placeholder="如 https://api.openai.com/v1" />
                  </el-form-item>
                  <el-form-item label="图像生成模型">
                    <el-input v-model="form.model.dalle.modelImage" placeholder="如 dall-e-3" />
                  </el-form-item>
                </div>
              </el-tab-pane>

              <el-tab-pane label="MiniMax" name="minimax">
                <div class="form-grid">
                  <el-form-item label="API Key">
                    <el-input
                      v-model="form.model.minimax.apiKey"
                      placeholder="脱敏显示，如需修改请清空后输入新值"
                      show-password
                    />
                    <div class="field-hint">敏感字段，保存时若仍含 **** 将跳过写入</div>
                  </el-form-item>
                  <el-form-item label="接口基础地址">
                    <el-input v-model="form.model.minimax.baseUrl" placeholder="如 https://api.minimaxi.com/v1" />
                  </el-form-item>
                  <el-form-item label="图像生成模型">
                    <el-input v-model="form.model.minimax.modelImage" placeholder="如 image-01 / image-01-live" />
                  </el-form-item>
                  <el-form-item label="AI 水印">
                    <el-switch v-model="form.model.minimax.watermark" :active-value="true" :inactive-value="false" active-text="开启" inactive-text="关闭" />
                    <div class="field-hint">开启后将在生成图片上添加「AI 生成」水印</div>
                  </el-form-item>
                  <el-form-item label="图片宽度（像素）">
                    <el-input-number v-model="form.model.minimax.width" :min="512" :max="2048" :step="8" controls-position="right" placeholder="留空不设置" />
                    <div class="field-hint">取值范围 512-2048，且必须是 8 的倍数</div>
                  </el-form-item>
                  <el-form-item label="图片高度（像素）">
                    <el-input-number v-model="form.model.minimax.height" :min="512" :max="2048" :step="8" controls-position="right" placeholder="留空不设置" />
                    <div class="field-hint">取值范围 512-2048，且必须是 8 的倍数</div>
                  </el-form-item>
                  <el-form-item label="随机数种子">
                    <el-input-number v-model="form.model.minimax.seed" :min="0" controls-position="right" placeholder="留空使用随机种子" />
                    <div class="field-hint">固定种子可使生成结果相对稳定</div>
                  </el-form-item>
                </div>
              </el-tab-pane>

              <el-tab-pane label="火山引擎 (Seedream)" name="volcengine">
                <div class="form-grid">
                  <el-form-item label="API Key">
                    <el-input
                      v-model="form.model.volcengine.apiKey"
                      placeholder="脱敏显示，如需修改请清空后输入新值"
                      show-password
                    />
                    <div class="field-hint">敏感字段，保存时若仍含 **** 将跳过写入。在方舟平台获取 API Key</div>
                  </el-form-item>
                  <el-form-item label="接口基础地址">
                    <el-input
                      v-model="form.model.volcengine.baseUrl"
                      placeholder="如 https://ark.cn-beijing.volces.com/api/v3"
                    />
                  </el-form-item>
                  <el-form-item label="图像生成模型">
                    <el-input
                      v-model="form.model.volcengine.modelImage"
                      placeholder="如 seedream-5-0-pro"
                    />
                    <div class="field-hint">可选：seedream-5-0-pro / seedream-5-0-lite / seedream-4-5 / seedream-4-0</div>
                  </el-form-item>
                  <el-form-item label="AI 水印">
                    <el-switch v-model="form.model.volcengine.watermark" :active-value="true" :inactive-value="false" active-text="开启" inactive-text="关闭" />
                    <div class="field-hint">开启后将在生成图片右下角添加「AI 生成」水印</div>
                  </el-form-item>
                  <el-form-item label="图片宽度（像素）">
                    <el-input-number v-model="form.model.volcengine.width" :min="512" :max="2048" :step="8" controls-position="right" placeholder="留空不设置" />
                  </el-form-item>
                  <el-form-item label="图片高度（像素）">
                    <el-input-number v-model="form.model.volcengine.height" :min="512" :max="2048" :step="8" controls-position="right" placeholder="留空不设置" />
                  </el-form-item>
                  <el-form-item label="随机数种子">
                    <el-input-number v-model="form.model.volcengine.seed" :min="0" controls-position="right" placeholder="留空使用随机种子" />
                    <div class="field-hint">固定种子可使生成结果相对稳定</div>
                  </el-form-item>
                </div>
              </el-tab-pane>
            </el-tabs>
          </section>

          <!-- 存储配置 -->
          <section class="notebook-section ink-fade ink-fade--delay-2">
            <h2 class="notebook-section__label font-display">
              <span class="ink-stamp">贰</span>
              <span>图片存储</span>
            </h2>

            <el-form-item label="存储类型" class="default-provider-item">
              <el-select v-model="form.storage.storageType" class="w-full">
                <el-option
                  v-for="opt in storageTypeOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
              <div class="field-hint">切换后将显示对应存储的配置项</div>
            </el-form-item>

            <div v-if="form.storage.storageType === 'minio'" class="form-grid">
              <el-form-item label="MinIO 端点">
                <el-input v-model="form.storage.minio.endpoint" placeholder="不含协议，如 localhost:9000" />
              </el-form-item>
              <el-form-item label="MinIO Access Key">
                <el-input
                  v-model="form.storage.minio.accessKey"
                  placeholder="脱敏显示，如需修改请清空后输入"
                  show-password
                />
                <div class="field-hint">敏感字段，保存时若仍含 **** 将跳过写入</div>
              </el-form-item>
              <el-form-item label="MinIO Secret Key">
                <el-input
                  v-model="form.storage.minio.secretKey"
                  placeholder="脱敏显示，如需修改请清空后输入"
                  show-password
                />
                <div class="field-hint">敏感字段，保存时若仍含 **** 将跳过写入</div>
              </el-form-item>
              <el-form-item label="存储桶名称">
                <el-input v-model="form.storage.minio.bucket" placeholder="如 photostyle" />
              </el-form-item>
              <el-form-item label="启用 HTTPS">
                <el-switch v-model="form.storage.minio.secure" />
              </el-form-item>
              <el-form-item label="对外访问基地址">
                <el-input
                  v-model="form.storage.minio.publicBaseUrl"
                  placeholder="如 https://example.com"
                />
              </el-form-item>
            </div>

            <div v-else-if="form.storage.storageType === 'oss'" class="form-grid">
              <el-form-item label="OSS Access Key ID">
                <el-input
                  v-model="form.storage.oss.accessKeyId"
                  placeholder="脱敏显示，如需修改请清空后输入"
                  show-password
                />
                <div class="field-hint">敏感字段，保存时若仍含 **** 将跳过写入</div>
              </el-form-item>
              <el-form-item label="OSS Access Key Secret">
                <el-input
                  v-model="form.storage.oss.accessKeySecret"
                  placeholder="脱敏显示，如需修改请清空后输入"
                  show-password
                />
                <div class="field-hint">敏感字段，保存时若仍含 **** 将跳过写入</div>
              </el-form-item>
              <el-form-item label="存储桶名称">
                <el-input v-model="form.storage.oss.bucket" placeholder="如 photostyle" />
              </el-form-item>
              <el-form-item label="OSS 端点">
                <el-input
                  v-model="form.storage.oss.endpoint"
                  placeholder="如 https://oss-cn-hangzhou.aliyuncs.com"
                />
              </el-form-item>
            </div>
          </section>

          <!-- 应用配置 -->
          <section class="notebook-section ink-fade ink-fade--delay-3">
            <h2 class="notebook-section__label font-display">
              <span class="ink-stamp">叁</span>
              <span>应用配置</span>
            </h2>
            <div class="form-grid">
              <el-form-item label="日志级别">
                <el-select v-model="form.app.logLevel" class="w-full">
                  <el-option v-for="lvl in logLevelOptions" :key="lvl" :label="lvl" :value="lvl" />
                </el-select>
              </el-form-item>
              <el-form-item label="CORS 允许来源">
                <el-input
                  v-model="form.app.corsAllowedOrigins"
                  type="textarea"
                  :rows="2"
                  placeholder="多个来源用英文逗号分隔"
                />
              </el-form-item>
              <el-form-item label="每次转换扣除积分">
                <el-input-number v-model="form.app.rateLimitCreditCostPerConvert" :min="0" :max="1000" />
              </el-form-item>
              <el-form-item label="Access Token 过期时间（分钟）">
                <el-input-number v-model="form.app.accessTokenExpireMinutes" :min="1" :max="10080" />
              </el-form-item>
            </div>
          </section>

          <!-- 操作区 -->
          <div class="admin-actions">
            <div class="restart-tip">
              <span class="restart-tip__icon">!</span>
              <span>模型配置保存到数据库立即生效；存储/应用配置写入 .env 后需重启后端服务</span>
            </div>
            <div class="admin-actions__btns">
              <el-button :disabled="saving" @click="onReset">重新加载</el-button>
              <el-button type="primary" :loading="saving" @click="onSave">保存配置</el-button>
            </div>
          </div>
        </el-form>
      </el-tab-pane>

      <!-- 用户管理（仅拥有 admin:users 权限可见） -->
      <el-tab-pane v-if="canManageUsers" label="用户管理" name="users">
        <div class="user-manage">
          <div class="user-manage__head">
            <span class="user-manage__count">共 {{ userTotal }} 位用户</span>
            <el-button size="small" :loading="usersLoading" @click="loadUsers">刷新</el-button>
          </div>

          <el-table :data="users" v-loading="usersLoading" class="user-table" stripe>
            <el-table-column label="用户" min-width="240">
              <template #default="{ row }">
                <div class="user-cell">
                  <img v-if="row.avatarUrl" :src="row.avatarUrl" class="user-cell__avatar" alt="" />
                  <span v-else class="user-cell__avatar user-cell__avatar--default">
                    {{ (row.nickname || row.email || '?').charAt(0).toUpperCase() }}
                  </span>
                  <div class="user-cell__meta">
                    <div class="user-cell__name">{{ row.nickname || '—' }}</div>
                    <div class="user-cell__email">{{ row.email }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
                  {{ row.status === 'active' ? '正常' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="管理员" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.isAdmin" type="warning" size="small">是</el-tag>
                <span v-else class="text-muted">否</span>
              </template>
            </el-table-column>
            <el-table-column label="权限" min-width="280">
              <template #default="{ row }">
                <el-tag
                  v-for="p in row.permissions"
                  :key="p"
                  size="small"
                  class="perm-tag"
                >
                  {{ p }}
                </el-tag>
                <span v-if="!row.permissions.length" class="text-muted">无</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" link @click="openEdit(row as AdminUserItem)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="user-pager"
            layout="prev, pager, next"
            :total="userTotal"
            :page-size="userPageSize"
            :current-page="userPage"
            @current-change="onUserPageChange"
          />
        </div>
      </el-tab-pane>

      <!-- 技能管理 -->
      <el-tab-pane label="技能管理" name="skills">
        <SkillManager />
      </el-tab-pane>

      <!-- 反馈管理 -->
      <el-tab-pane label="反馈管理" name="feedbacks">
        <FeedbackManager />
      </el-tab-pane>
    </el-tabs>

    <!-- 用户编辑弹窗 -->
    <el-dialog
      v-model="editVisible"
      title="编辑用户"
      width="600px"
      align-center
    >
      <div v-if="editing" class="user-edit">
        <div class="user-edit__avatar">
          <img v-if="avatarPreview" :src="avatarPreview" class="user-edit__avatar-img" alt="" />
          <div v-else class="user-edit__avatar-img user-edit__avatar-img--default">
            {{ (editForm.nickname || editing.email || '?').charAt(0).toUpperCase() }}
          </div>
          <el-button size="small" :loading="editUploading" @click="triggerEditUpload">
            {{ editUploading ? '上传中…' : '更换头像' }}
          </el-button>
          <input
            ref="editFileInput"
            type="file"
            accept="image/*"
            class="user-edit__input"
            @change="onEditFileChange"
          />
        </div>

        <el-form label-position="top">
          <el-form-item label="昵称">
            <el-input v-model="editForm.nickname" maxlength="32" />
          </el-form-item>
          <el-form-item label="账号状态">
            <el-select v-model="editForm.status" class="w-full">
              <el-option label="正常" value="active" />
              <el-option label="禁用" value="disabled" />
            </el-select>
          </el-form-item>
          <el-form-item label="管理员">
            <el-switch v-model="editForm.isAdmin" />
            <span class="field-hint">开启后该用户拥有全部权限，并可分配他人权限</span>
          </el-form-item>
          <el-form-item label="角色预设（快速分配）">
            <el-select
              v-model="rolePresetKey"
              placeholder="选择角色快速填充权限"
              class="w-full"
              clearable
              @change="applyRolePreset"
            >
              <el-option
                v-for="p in catalog?.rolePresets || []"
                :key="p.key"
                :label="p.label"
                :value="p.key"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="权限分配">
            <el-checkbox-group v-model="editForm.permissions" class="perm-group">
              <el-checkbox
                v-for="perm in catalog?.permissions || []"
                :key="perm.code"
                :value="perm.code"
                border
              >
                {{ perm.label }}
                <span class="perm-code">{{ perm.code }}</span>
              </el-checkbox>
            </el-checkbox-group>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingUser" @click="onSaveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-page {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* 标题区：与首页一致的水墨呼吸 */
.hero {
  text-align: center;
  margin-bottom: 8px;
}
.hero__seal-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 14px;
}
.hero__seal {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 28px;
  line-height: 48px;
  text-align: center;
  box-shadow: var(--shadow-seal);
  position: relative;
}
.hero__seal::after {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 7px;
  height: 7px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 50%;
}
.hero__title {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.1em;
  margin-bottom: 6px;
}
.hero__subtitle {
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}

.admin-tabs {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 8px 32px 32px;
  box-shadow: var(--shadow-sm);
}
.admin-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}
.admin-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}
.admin-tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary);
}
.admin-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--color-primary);
}

/* 分区表单：复用 notebook-section 风格 + 纸张质感 */
.notebook-section {
  position: relative;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 28px 36px;
  box-shadow: 0 2px 8px rgba(156, 150, 139, 0.08),
              inset 0 1px 0 rgba(250, 248, 243, 0.5);
  margin-bottom: 24px;
  overflow: hidden;
  animation: section-fade-in 0.5s ease-out backwards;
}
.notebook-section::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.018;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  border-radius: inherit;
}
.notebook-section:nth-child(2) { animation-delay: 0.1s; }
.notebook-section:nth-child(3) { animation-delay: 0.2s; }

@keyframes section-fade-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.notebook-section__label {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 20px;
}
.ink-stamp {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: var(--color-primary);
  color: #fff;
  font-size: 16px;
  line-height: 28px;
  text-align: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-seal);
}

/* 默认 provider / 存储类型选择项：占满宽度 */
.default-provider-item {
  margin-bottom: 16px;
}
.default-provider-item :deep(.el-form-item__label) {
  font-size: 13px;
  color: var(--color-text);
  font-weight: 500;
}

/* provider tabs：保持水墨简洁 */
.provider-tabs {
  margin-top: 4px;
}
.provider-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}
.provider-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}
.provider-tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary);
}
.provider-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--color-primary);
}
.provider-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: var(--color-border);
  height: 1px;
}

/* 表单网格：双列布局，窄屏单列 */
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 24px;
}
.form-grid :deep(.el-form-item__label) {
  font-size: 13px;
  color: var(--color-text);
  font-weight: 500;
  padding-bottom: 4px;
}
.form-grid :deep(.el-input__wrapper),
.form-grid :deep(.el-textarea__inner),
.form-grid :deep(.el-select__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--color-border) inset;
  transition: box-shadow 0.2s;
}
.form-grid :deep(.el-input__wrapper.is-focus),
.form-grid :deep(.el-textarea__inner:focus),
.form-grid :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--color-primary) inset;
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

/* 启用模型多选框：茶色底、朱砂勾选 */
.enabled-providers-item {
  margin-bottom: 20px;
}
.enabled-providers-item :deep(.el-form-item__label) {
  font-size: 13px;
  color: var(--color-text);
  font-weight: 500;
}
.enabled-providers-item :deep(.el-checkbox-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.enabled-providers-item :deep(.el-checkbox) {
  margin: 0;
  padding: 6px 14px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  transition: all 0.2s ease;
}
.enabled-providers-item :deep(.el-checkbox.is-checked) {
  background: rgba(200, 68, 43, 0.06);
  border-color: rgba(200, 68, 43, 0.3);
}
.enabled-providers-item :deep(.el-checkbox__label) {
  font-size: 13px;
  color: var(--color-text);
  padding-left: 6px;
}
.enabled-providers-item :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}
.enabled-providers-item :deep(.el-checkbox__inner) {
  width: 14px;
  height: 14px;
  border-radius: 3px;
}

.w-full {
  width: 100%;
}

/* 操作区 */
.admin-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
  padding: 20px 0 8px;
}
.restart-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(200, 68, 43, 0.06);
  border: 1px solid rgba(200, 68, 43, 0.2);
  border-radius: 8px;
  font-size: 13px;
  color: var(--color-primary-dark);
}
.restart-tip__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.admin-actions__btns {
  display: flex;
  gap: 12px;
}
.admin-actions__btns :deep(.el-button) {
  border-radius: 8px;
  letter-spacing: 0.06em;
  padding: 10px 24px;
}

/* 用户管理 */
.user-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.user-manage__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.user-manage__count {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.user-table {
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-cell__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}
.user-cell__avatar--default {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}
.user-cell__name {
  font-size: 14px;
  color: var(--color-text);
}
.user-cell__email {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.perm-tag {
  margin: 2px 4px 2px 0;
}
.text-muted {
  color: var(--color-text-secondary);
  font-size: 13px;
}
.user-pager {
  display: flex;
  justify-content: center;
}

/* 用户编辑弹窗 */
.user-edit {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.user-edit__avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.user-edit__avatar-img {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--color-border);
}
.user-edit__avatar-img--default {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #fff;
  font-size: 28px;
  font-weight: 700;
}
.user-edit__input {
  display: none;
}
.perm-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.perm-code {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-left: 4px;
}

/* 窄屏单列 */
@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .notebook-section {
    padding: 20px 18px;
  }
  .admin-tabs {
    padding: 8px 16px 20px;
  }
}

/* 中等屏幕两列 */
@media (min-width: 641px) and (max-width: 1024px) {
  .form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* 宽屏三列 */
@media (min-width: 1025px) {
  .form-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
