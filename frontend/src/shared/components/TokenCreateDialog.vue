<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import PermissionPicker from '@/shared/components/PermissionPicker.vue'

export interface TokenForm {
  name: string
  permissions: string[]
  expires_at: string | null
}

const props = defineProps<{
  title: string
  saving: boolean
  createdSecret: string | null
  // Permissions every token of this dialog carries; the picker leaves them out.
  fixedPermissions?: string[]
  // Permissions the picker does not offer here.
  excludePermissions?: string[]
  // The longest lifetime in days this kind of token may have.
  maxDays?: number
  hint?: string
}>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ submit: [form: TokenForm] }>()

const { t } = useI18n()

// New tokens default to 90 days; the instance caps the lifetime anyway.
const DEFAULT_DAYS = 90
const DAY_MS = 24 * 60 * 60 * 1000

const name = ref('')
const permissions = ref<string[]>([])
const expires = ref<Date | null>(null)

watch(visible, (open) => {
  if (!open) return
  name.value = ''
  permissions.value = []
  expires.value = new Date(Date.now() + Math.min(DEFAULT_DAYS, props.maxDays ?? DEFAULT_DAYS) * DAY_MS)
})

const tomorrow = computed(() => new Date(Date.now() + DAY_MS))
const latest = computed(() => (props.maxDays ? new Date(Date.now() + props.maxDays * DAY_MS) : undefined))
const hidden = computed(() => [...(props.fixedPermissions ?? []), ...(props.excludePermissions ?? [])])

function submit() {
  emit('submit', {
    name: name.value,
    permissions: [...(props.fixedPermissions ?? []), ...permissions.value],
    expires_at: expires.value ? expires.value.toISOString() : null,
  })
}

async function copy() {
  if (props.createdSecret) await navigator.clipboard.writeText(props.createdSecret)
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="title" class="token-dialog">
    <div v-if="createdSecret" class="created">
      <Message severity="warn" :closable="false">{{ t('tokens.createdHint') }}</Message>
      <div class="secret-row">
        <code class="secret">{{ createdSecret }}</code>
        <Button icon="mdi mdi-content-copy" text :aria-label="t('common.copy')" @click="copy" />
      </div>
    </div>
    <form v-else id="token-form" class="form" @submit.prevent="submit">
      <p v-if="hint" class="hint">{{ hint }}</p>
      <div class="field">
        <label for="token-name">{{ t('common.name') }}</label>
        <InputText id="token-name" v-model="name" maxlength="64" />
      </div>
      <div class="field">
        <label for="token-permissions">{{ t('tokens.permissions') }}</label>
        <PermissionPicker v-model="permissions" input-id="token-permissions" for-token :exclude="hidden" />
      </div>
      <div class="field">
        <label for="token-expires">{{ t('tokens.expires') }}</label>
        <DatePicker v-model="expires" input-id="token-expires" :min-date="tomorrow" :max-date="latest" show-icon />
      </div>
    </form>
    <template #footer>
      <Button
        :label="createdSecret ? t('common.close') : t('common.cancel')"
        text
        @click="visible = false"
      />
      <Button
        v-if="!createdSecret"
        type="submit"
        form="token-form"
        :label="t('common.create')"
        :loading="saving"
        :disabled="!name"
      />
    </template>
  </Dialog>
</template>

<style scoped lang="scss">
.token-dialog {
  width: var(--dialog-width-sm);
}

.form,
.created {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.secret-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.secret {
  flex: 1;
  padding: var(--space-2);
  border-radius: var(--p-border-radius-sm);
  background: var(--p-content-hover-background);
  word-break: break-all;
  user-select: all;
}
</style>
