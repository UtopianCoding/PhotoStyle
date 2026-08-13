<script setup lang="ts">
// 模型服务方选择器：下拉选择模型提供方
import type { Provider } from '@/types'

defineProps<{
  providers: Provider[]
  modelValue?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

function onChange(value: string | number | boolean | string[]) {
  emit('update:modelValue', String(value))
}
</script>

<template>
  <el-select
    :model-value="modelValue"
    placeholder="选择模型服务方"
    class="w-full"
    @change="onChange"
  >
    <el-option
      v-for="p in providers"
      :key="p.id"
      :label="p.name"
      :value="p.id"
    />
  </el-select>
</template>
