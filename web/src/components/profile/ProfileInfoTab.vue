<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { updateMe, uploadAvatar } from '@/api/user'

const userStore = useUserStore()

const nickname = ref('')
const avatarUrl = ref('')
const avatarPreview = ref('')
const initialNickname = ref('')
const initialAvatar = ref('')
const saving = ref(false)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

/** 是否有未保存的修改 */
const dirty = computed(
  () => nickname.value !== initialNickname.value || avatarPreview.value !== initialAvatar.value,
)

/** 初始化用户资料 */
function initUserData() {
  nickname.value = userStore.nickname
  avatarUrl.value = userStore.avatarUrl
  avatarPreview.value = userStore.avatarUrl
  initialNickname.value = userStore.nickname
  initialAvatar.value = userStore.avatarUrl
}

// 监听 userStore 变化，自动同步
watch(
  () => [userStore.nickname, userStore.avatarUrl],
  () => {
    initUserData()
  },
  { immediate: true },
)

/** 触发文件选择 */
function triggerUpload() {
  fileInput.value?.click()
}

/** 选择头像文件后上传 */
async function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    target.value = ''
    return
  }
  uploading.value = true
  try {
    const res = await uploadAvatar(file)
    avatarUrl.value = res.avatarUrl
    avatarPreview.value = res.avatarUrl
    ElMessage.success('头像已上传，点击保存生效')
  } catch {
    // 拦截器已提示
  } finally {
    uploading.value = false
    target.value = ''
  }
}

/** 保存资料 */
async function onSave() {
  saving.value = true
  try {
    const res = await updateMe({
      nickname: nickname.value,
      avatarUrl: avatarUrl.value || null,
    })
    userStore.updateLocalProfile({
      nickname: res.nickname,
      avatarUrl: res.avatarUrl ?? '',
      permissions: res.permissions,
      isAdmin: res.isAdmin,
    })
    // 更新初始值
    initialNickname.value = res.nickname
    initialAvatar.value = res.avatarUrl ?? ''
    ElMessage.success('资料已保存')
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}

/** 重置修改 */
function onReset() {
  nickname.value = initialNickname.value
  avatarPreview.value = initialAvatar.value
  avatarUrl.value = initialAvatar.value
}
</script>

<template>
  <div class="profile-info-tab">
    <!-- 头像区域：居中展示，纸张纹理背景 -->
    <section class="avatar-section">
      <div class="avatar-section__bg"></div>
      <div class="avatar-section__content">
        <button
          type="button"
          class="avatar-btn"
          :class="{ 'is-uploading': uploading }"
          @click="triggerUpload"
        >
          <img
            v-if="avatarPreview"
            :src="avatarPreview"
            class="avatar-img"
            alt="头像预览"
          />
          <span v-else class="avatar-img avatar-img--default">
            {{ (nickname || userStore.email || '?').charAt(0).toUpperCase() }}
          </span>
          <!-- 悬浮遮罩 -->
          <span class="avatar-overlay">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            <span>更换头像</span>
          </span>
          <!-- 上传中蒙层 -->
          <span v-if="uploading" class="avatar-loading">
            <span class="avatar-spinner"></span>
          </span>
        </button>
        <p class="avatar-hint">点击更换头像 · 支持 JPG / PNG</p>
      </div>
      <!-- 朱砂笔触分隔线 -->
      <div class="ink-divider"></div>
    </section>

    <!-- 表单卡片 -->
    <section class="form-card">
      <!-- 邮箱（只读） -->
      <div class="form-field">
        <label class="form-field__label">
          <span class="form-field__dot"></span>
          邮箱
        </label>
        <div class="form-field__readonly">
          <span class="form-field__value">{{ userStore.email }}</span>
          <span class="form-field__badge">不可修改</span>
        </div>
        <p class="form-field__hint">如需更换邮箱，请联系管理员</p>
      </div>

      <!-- 分割线 -->
      <div class="form-divider"></div>

      <!-- 昵称 -->
      <div class="form-field">
        <label class="form-field__label">
          <span class="form-field__dot"></span>
          昵称
        </label>
        <div class="form-field__input-wrap">
          <input
            v-model="nickname"
            type="text"
            class="form-field__input"
            :class="{ 'is-dirty': dirty && nickname !== initialNickname }"
            placeholder="请输入你的昵称"
            maxlength="32"
          />
          <span class="form-field__counter">{{ nickname.length }}/32</span>
        </div>
        <p class="form-field__hint">昵称将显示在个人资料和评论中</p>
      </div>
    </section>

    <!-- 未保存提示条 -->
    <transition name="slide-hint">
      <div v-if="dirty" class="unsaved-bar">
        <span class="unsaved-bar__dot"></span>
        <span class="unsaved-bar__text">有未保存的修改</span>
        <div class="unsaved-bar__actions">
          <button type="button" class="unsaved-bar__btn unsaved-bar__btn--reset" @click="onReset">
            重置
          </button>
          <button
            type="button"
            class="unsaved-bar__btn unsaved-bar__btn--save"
            :disabled="saving"
            @click="onSave"
          >
            {{ saving ? '保存中…' : '保存修改' }}
          </button>
        </div>
      </div>
    </transition>

    <!-- 无修改时的底部占位 -->
    <div v-if="!dirty" class="bottom-spacer">
      <el-button
        type="primary"
        size="large"
        :loading="saving"
        :disabled="!dirty"
        @click="onSave"
        class="save-btn"
      >
        保存修改
      </el-button>
    </div>

    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      style="display: none"
      @change="onFileChange"
    />
  </div>
</template>

<style scoped>
.profile-info-tab {
  max-width: 600px;
  margin: 0 auto;
  padding: 8px 0;
}

/* ==================== 头像区域 ==================== */
.avatar-section {
  position: relative;
  padding: 32px 0 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.avatar-section__bg {
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  background:
    radial-gradient(ellipse at 50% 20%, rgba(200, 68, 43, 0.04) 0%, transparent 60%),
    var(--color-bg-card);
  border: 1px solid var(--color-border);
  pointer-events: none;
}

.avatar-section__bg::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.02;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  border-radius: inherit;
}

.avatar-section__content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.avatar-btn {
  position: relative;
  width: 108px;
  height: 108px;
  padding: 0;
  border: none;
  background: none;
  border-radius: 50%;
  cursor: pointer;
  box-shadow:
    0 0 0 4px rgba(200, 68, 43, 0.08),
    0 6px 20px rgba(156, 150, 139, 0.15);
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
}

.avatar-btn:hover {
  transform: scale(1.05);
  box-shadow:
    0 0 0 5px rgba(200, 68, 43, 0.14),
    0 10px 28px rgba(156, 150, 139, 0.2);
}

.avatar-btn:active:not(.is-uploading) {
  transform: scale(0.98);
}

.avatar-btn.is-uploading {
  pointer-events: none;
}

.avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
}

.avatar-img--default {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: #faf8f3;
  font-size: 42px;
  font-weight: 700;
  font-family: var(--font-display);
  letter-spacing: -0.02em;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  color: #faf8f3;
  background: rgba(28, 28, 26, 0.5);
  backdrop-filter: blur(3px);
  opacity: 0;
  transition: opacity 0.25s ease;
}

.avatar-overlay span {
  font-size: 11px;
  letter-spacing: 0.06em;
  font-family: var(--font-body);
}

.avatar-btn:hover .avatar-overlay {
  opacity: 1;
}

.avatar-loading {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(28, 28, 26, 0.45);
  backdrop-filter: blur(3px);
}

.avatar-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid rgba(255, 255, 255, 0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.avatar-hint {
  font-size: 12px;
  color: var(--color-text-placeholder);
  letter-spacing: 0.04em;
  margin: 0;
}

/* 朱砂笔触分隔线 */
.ink-divider {
  position: relative;
  z-index: 1;
  width: 48px;
  height: 2px;
  margin-top: 24px;
  background: linear-gradient(
    90deg,
    transparent,
    var(--color-primary) 25%,
    var(--color-primary) 75%,
    transparent
  );
  opacity: 0.5;
  border-radius: 1px;
}

/* ==================== 表单卡片 ==================== */
.form-card {
  margin-top: 24px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(156, 150, 139, 0.06),
              inset 0 1px 0 rgba(250, 248, 243, 0.6);
}

.form-card::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.016;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  border-radius: inherit;
}

.form-field {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-field__label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-text);
}

.form-field__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-primary);
  flex-shrink: 0;
}

/* 只读字段 */
.form-field__readonly {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.form-field__value {
  font-size: 15px;
  color: var(--color-text);
  font-family: var(--font-body);
  letter-spacing: 0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.form-field__badge {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--color-text-placeholder);
  background: rgba(156, 150, 139, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.form-field__hint {
  font-size: 12px;
  color: var(--color-text-placeholder);
  letter-spacing: 0.02em;
  margin: 0;
  line-height: 1.4;
}

/* 表单分割线 */
.form-divider {
  height: 1px;
  background: var(--color-border);
  margin: 20px 0;
  position: relative;
  z-index: 1;
}

/* 可编辑输入框 */
.form-field__input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.form-field__input {
  width: 100%;
  padding: 12px 56px 12px 16px;
  font-size: 15px;
  font-family: var(--font-body);
  color: var(--color-text);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  letter-spacing: 0.01em;
}

.form-field__input::placeholder {
  color: var(--color-text-placeholder);
}

.form-field__input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(200, 68, 43, 0.08);
}

.form-field__input.is-dirty {
  border-color: var(--color-primary-light);
}

.form-field__counter {
  position: absolute;
  right: 14px;
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--color-text-placeholder);
  pointer-events: none;
  user-select: none;
}

/* ==================== 未保存提示条 ==================== */
.unsaved-bar {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(200, 68, 43, 0.05);
  border: 1px solid rgba(200, 68, 43, 0.12);
  border-radius: var(--radius-md);
}

.unsaved-bar__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-primary);
  flex-shrink: 0;
  animation: pulse-dot 1.8s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}

.unsaved-bar__text {
  font-size: 13px;
  color: var(--color-primary);
  letter-spacing: 0.02em;
  flex: 1;
}

.unsaved-bar__actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.unsaved-bar__btn {
  padding: 6px 16px;
  font-size: 13px;
  font-family: var(--font-body);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
  letter-spacing: 0.04em;
  border: none;
}

.unsaved-bar__btn--reset {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.unsaved-bar__btn--reset:hover {
  background: rgba(156, 150, 139, 0.08);
  color: var(--color-text);
}

.unsaved-bar__btn--save {
  background: var(--color-primary);
  color: #fff;
}

.unsaved-bar__btn--save:hover {
  background: var(--color-primary-dark);
}

.unsaved-bar__btn--save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 滑入动画 */
.slide-hint-enter-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.slide-hint-leave-active {
  transition: all 0.2s ease;
}
.slide-hint-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.slide-hint-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 无修改时的底部占位 */
.bottom-spacer {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.save-btn {
  min-width: 120px;
  letter-spacing: 0.06em;
}

/* ==================== 响应式 ==================== */
@media (max-width: 640px) {
  .avatar-btn {
    width: 88px;
    height: 88px;
  }

  .avatar-img--default {
    font-size: 34px;
  }

  .form-card {
    padding: 20px 16px;
  }

  .form-field__readonly {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .unsaved-bar {
    flex-wrap: wrap;
  }

  .unsaved-bar__actions {
    width: 100%;
    margin-top: 4px;
  }

  .unsaved-bar__btn {
    flex: 1;
    text-align: center;
  }

  .bottom-spacer {
    justify-content: stretch;
  }

  .bottom-spacer .save-btn {
    width: 100%;
  }
}
</style>
