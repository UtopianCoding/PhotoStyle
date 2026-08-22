<script setup lang="ts">
// 个人资料弹窗：修改昵称、上传头像
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { updateMe, uploadAvatar } from '@/api/user'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

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

/** 打开弹窗时同步当前用户资料 */
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      nickname.value = userStore.nickname
      avatarUrl.value = userStore.avatarUrl
      avatarPreview.value = userStore.avatarUrl
      initialNickname.value = userStore.nickname
      initialAvatar.value = userStore.avatarUrl
    }
  },
  { immediate: true },
)

function close() {
  emit('update:modelValue', false)
}

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
    ElMessage.success('资料已保存')
    close()
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="420px"
    align-center
    :show-close="true"
    class="profile-dialog-root"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <template #header>
      <div class="profile-dialog__header">
        <span class="profile-dialog__header-seal">影</span>
        <span class="profile-dialog__header-title font-display">个人资料</span>
      </div>
    </template>

    <div class="profile-dialog">
      <!-- 头像区域：居中大头像 + 点击更换 -->
      <div class="profile-avatar-section">
        <button
          type="button"
          class="profile-avatar"
          :class="{ 'is-dirty': dirty, 'is-uploading': uploading }"
          @click="triggerUpload"
        >
          <img
            v-if="avatarPreview"
            :src="avatarPreview"
            class="profile-avatar__img"
            alt="头像预览"
          />
          <span v-else class="profile-avatar__img profile-avatar__img--default">
            {{ (nickname || userStore.email || '?').charAt(0).toUpperCase() }}
          </span>
          <!-- 悬浮遮罩 -->
          <span class="profile-avatar__overlay">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            <span>更换头像</span>
          </span>
          <!-- 上传中蒙层 -->
          <span v-if="uploading" class="profile-avatar__loading">
            <span class="profile-avatar__spinner"></span>
          </span>
        </button>
        <p class="profile-avatar__email font-mono-label">{{ userStore.email }}</p>
      </div>

      <!-- 表单区域 -->
      <div class="profile-form">
        <div class="profile-form__field">
          <label class="profile-form__label">
            <span class="profile-form__dot"></span>
            昵称
          </label>
          <el-input
            v-model="nickname"
            placeholder="请题写你的署名"
            maxlength="32"
            show-word-limit
            size="large"
          />
        </div>
      </div>

      <!-- 未保存提示 -->
      <transition name="fade-hint">
        <div v-if="dirty" class="profile-hint">
          <span class="profile-hint__dot"></span>
          有未保存的修改
        </div>
      </transition>
    </div>

    <template #footer>
      <div class="profile-dialog__footer">
        <el-button @click="close" size="large">取消</el-button>
        <el-button
          type="primary"
          size="large"
          :loading="saving"
          :disabled="!dirty"
          @click="onSave"
          class="profile-dialog__save-btn"
        >
          保存修改
        </el-button>
      </div>
    </template>

    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      class="profile-avatar__input"
      @change="onFileChange"
    />
  </el-dialog>
</template>

<style scoped>
/* 弹窗头部 */
.profile-dialog__header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.profile-dialog__header-seal {
  width: 24px;
  height: 24px;
  border-radius: 3px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 14px;
  line-height: 24px;
  text-align: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-seal);
}
.profile-dialog__header-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.08em;
}

/* 弹窗主体 */
.profile-dialog {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 头像区域 */
.profile-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 8px 0 4px;
}
.profile-avatar {
  position: relative;
  width: 96px;
  height: 96px;
  padding: 0;
  border: none;
  background: none;
  border-radius: 50%;
  cursor: pointer;
  box-shadow:
    0 0 0 3px rgba(200, 68, 43, 0.1),
    0 4px 16px rgba(156, 150, 139, 0.12);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.profile-avatar:hover {
  transform: scale(1.06);
  box-shadow:
    0 0 0 4px rgba(200, 68, 43, 0.18),
    0 8px 24px rgba(156, 150, 139, 0.18);
}
.profile-avatar.is-dirty {
  box-shadow:
    0 0 0 3px rgba(200, 68, 43, 0.3),
    0 4px 16px rgba(156, 150, 139, 0.12);
}
.profile-avatar.is-uploading {
  pointer-events: none;
}
.profile-avatar__img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
}
.profile-avatar__img--default {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: #faf8f3;
  font-size: 36px;
  font-weight: 700;
  font-family: var(--font-display);
}
.profile-avatar__overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #faf8f3;
  background: rgba(28, 28, 26, 0.55);
  backdrop-filter: blur(2px);
  opacity: 0;
  transition: opacity 0.25s ease;
}
.profile-avatar__overlay span {
  font-size: 11px;
  letter-spacing: 0.08em;
}
.profile-avatar:hover .profile-avatar__overlay {
  opacity: 1;
}
.profile-avatar__loading {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(28, 28, 26, 0.5);
  backdrop-filter: blur(2px);
}
.profile-avatar__spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.profile-avatar__email {
  font-size: 12px;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
}

/* 表单 */
.profile-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.profile-form__field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.profile-form__label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--color-text);
}
.profile-form__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-primary);
  flex-shrink: 0;
}

/* 未保存提示 */
.profile-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(200, 68, 43, 0.06);
  border: 1px solid rgba(200, 68, 43, 0.15);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--color-primary);
  letter-spacing: 0.02em;
}
.profile-hint__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  flex-shrink: 0;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.fade-hint-enter-active,
.fade-hint-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-hint-enter-from,
.fade-hint-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 底部按钮 */
.profile-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.profile-dialog__save-btn {
  min-width: 100px;
  letter-spacing: 0.06em;
}

/* 隐藏文件输入 */
.profile-avatar__input {
  display: none;
}

/* Element Plus 弹窗微调 */
:deep(.el-dialog__body) {
  padding-top: 16px;
  padding-bottom: 8px;
}
</style>
