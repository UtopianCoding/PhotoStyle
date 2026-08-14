<script setup lang="ts">
// 后台配置页：模型 / 存储 / 应用 三个分区表单，写入 .env 后需重启后端生效
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import * as adminApi from '@/api/admin'
import type { SystemConfig, SystemConfigUpdate } from '@/types'

// 表单引用
const formRef = ref<FormInstance>()
// 加载/保存中
const loading = ref(false)
const saving = ref(false)
// 模型 provider 当前激活的 tab（使用 provider_id：qianwen / dalle / minimax）
const activeProviderTab = ref<'qianwen' | 'dalle' | 'minimax'>('qianwen')

// 表单数据：直接对齐后端字段，CORS 来源用逗号分隔字符串维护
const form = reactive({
  model: {
    defaultProvider: 'qianwen',
    qianwen: {
      apiKey: '',
      modelVision: '',
      modelImage: '',
      workspaceId: '',
      region: '',
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
    rateLimitFreeUserDailyLimit: 10,
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
]

/** 加载当前系统配置 */
async function loadConfig() {
  loading.value = true
  try {
    const data: SystemConfig = await adminApi.getSystemConfig()
    fillForm(data)
    // 默认激活 tab 跟随 defaultProvider
    const dp = data.model.defaultProvider
    if (dp === 'dalle' || dp === 'minimax' || dp === 'qianwen') {
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
  form.model.qianwen = { ...data.model.qianwen }
  form.model.dalle = { ...data.model.dalle }
  form.model.minimax = { ...data.model.minimax }

  form.storage.storageType = data.storage.storageType
  form.storage.minio = { ...data.storage.minio }
  form.storage.oss = { ...data.storage.oss }

  form.app.logLevel = data.app.logLevel
  form.app.corsAllowedOrigins = data.app.corsAllowedOrigins.join(', ')
  form.app.rateLimitFreeUserDailyLimit = data.app.rateLimitFreeUserDailyLimit
  form.app.accessTokenExpireMinutes = data.app.accessTokenExpireMinutes
}

/** 构造更新 payload：敏感字段若仍为脱敏形态则跳过，避免覆盖为脏值 */
function buildPayload(): SystemConfigUpdate {
  const payload: SystemConfigUpdate = {}

  // 模型配置
  const model: NonNullable<SystemConfigUpdate['model']> = {
    defaultProvider: form.model.defaultProvider,
  }
  // 千问
  const ds = form.model.qianwen
  const qianwen: NonNullable<NonNullable<SystemConfigUpdate['model']>['qianwen']> = {}
  if (ds.apiKey && !ds.apiKey.includes('****')) qianwen.apiKey = ds.apiKey
  if (ds.modelVision) qianwen.modelVision = ds.modelVision
  if (ds.modelImage) qianwen.modelImage = ds.modelImage
  qianwen.workspaceId = ds.workspaceId
  if (ds.region) qianwen.region = ds.region
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
  if (Object.keys(minimax).length > 0) model.minimax = minimax
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
  app.rateLimitFreeUserDailyLimit = form.app.rateLimitFreeUserDailyLimit
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
    ElMessage.success('配置已写入 .env，请重启后端服务使新配置生效')
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

onMounted(loadConfig)
</script>

<template>
  <div v-loading="loading" class="admin-page mx-auto max-w-4xl px-4 py-10">
    <!-- 标题区 -->
    <section class="hero ink-fade">
      <div class="hero__seal-wrap">
        <span class="hero__seal">管</span>
      </div>
      <h1 class="hero__title font-display">后台配置</h1>
      <p class="hero__subtitle">管理模型参数、图片存储与应用配置，修改后需重启后端生效</p>
    </section>

    <el-form ref="formRef" :model="form" label-position="top" class="admin-form">
      <!-- 模型配置 -->
      <section class="notebook-section ink-fade ink-fade--delay-1">
        <h2 class="notebook-section__label font-display">
          <span class="ink-stamp">壹</span>
          <span>模型配置</span>
        </h2>

        <!-- 默认 provider 选择 -->
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

        <!-- 三个 provider 配置：tab 切换 -->
        <el-tabs v-model="activeProviderTab" class="provider-tabs">
          <!-- 千问 / DashScope -->
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
            </div>
          </el-tab-pane>

          <!-- OpenAI / DALL-E -->
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

          <!-- MiniMax -->
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
                <el-input v-model="form.model.minimax.baseUrl" placeholder="如 https://api.minimax.chat/v1" />
              </el-form-item>
              <el-form-item label="图像生成模型">
                <el-input v-model="form.model.minimax.modelImage" placeholder="如 image-01" />
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

        <!-- 存储类型选择 -->
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

        <!-- MinIO 配置（storageType === 'minio' 时显示） -->
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

        <!-- OSS 配置（storageType === 'oss' 时显示） -->
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
          <el-form-item label="免费用户每日限额">
            <el-input-number v-model="form.app.rateLimitFreeUserDailyLimit" :min="0" :max="1000" />
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
          <span>配置写入 .env 后，需重启后端服务才能让新配置在内存中生效</span>
        </div>
        <div class="admin-actions__btns">
          <el-button :disabled="saving" @click="onReset">重新加载</el-button>
          <el-button type="primary" :loading="saving" @click="onSave">保存配置</el-button>
        </div>
      </div>
    </el-form>
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

/* 分区表单：复用 notebook-section 风格 */
.notebook-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px 28px;
  box-shadow: var(--shadow-sm);
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

/* 窄屏单列 */
@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .notebook-section {
    padding: 20px 18px;
  }
}
</style>
