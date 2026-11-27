<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { ALL_PERMISSIONS } from '@/core/auth/permissions'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const props = defineProps<{
  inputId: string
  // For a token: the permissions a token can never carry are left out.
  forToken?: boolean
  // Permissions the caller handles itself, such as the fixed `use:mcp` of an agent token.
  exclude?: string[]
}>()
const model = defineModel<string[]>({ required: true })

const { t } = useI18n()
const currentUser = useCurrentUserStore()

const TOKEN_BLOCKED = new Set([
  'write:settings',
  'write:users',
  'write:groups',
  'manage:api_keys',
  'write:pat',
])

// Nobody can grant what they do not hold, so the list only offers those.
const options = computed(() =>
  ALL_PERMISSIONS.filter((p) => currentUser.hasPermission(p))
    .filter((p) => !props.forToken || !TOKEN_BLOCKED.has(p))
    .filter((p) => !props.exclude?.includes(p))
    .map((p) => ({ value: p, label: t(`permissions.${p.replace(':', '_')}`) })),
)
</script>

<template>
  <MultiSelect
    v-model="model"
    :input-id="inputId"
    :options="options"
    option-label="label"
    option-value="value"
    display="chip"
    filter
    :placeholder="t('common.none')"
    class="permission-picker"
  />
</template>

<style scoped lang="scss">
.permission-picker {
  width: 100%;
}
</style>
