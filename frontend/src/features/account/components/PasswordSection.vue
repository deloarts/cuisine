<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { changePassword } from '@/features/account/api/security'
import { useAppToast } from '@/core/composables/useAppToast'

const { t } = useI18n()
const toast = useAppToast()

const current = ref('')
const next = ref('')
const repeat = ref('')
const saving = ref(false)

const mismatch = computed(() => repeat.value !== '' && next.value !== repeat.value)

async function change() {
  saving.value = true
  try {
    await changePassword(current.value, next.value)
    current.value = next.value = repeat.value = ''
    toast.success(t('account.password.changed'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="section" @submit.prevent="change">
    <h2 class="panel-title">{{ t('account.password.title') }}</h2>
    <p class="hint">{{ t('account.password.hint') }}</p>
    <div class="form-grid">
      <div class="field">
        <label for="pw-current">{{ t('account.password.current') }}</label>
        <Password
          v-model="current"
          input-id="pw-current"
          :feedback="false"
          toggle-mask
          autocomplete="current-password"
        />
      </div>
      <div />
      <div class="field">
        <label for="pw-new">{{ t('account.password.new') }}</label>
        <Password v-model="next" input-id="pw-new" toggle-mask autocomplete="new-password" />
      </div>
      <div class="field">
        <label for="pw-repeat">{{ t('account.password.repeat') }}</label>
        <Password
          v-model="repeat"
          input-id="pw-repeat"
          :feedback="false"
          toggle-mask
          autocomplete="new-password"
          :invalid="mismatch"
        />
        <small v-if="mismatch" class="field-hint">{{ t('account.password.mismatch') }}</small>
      </div>
    </div>
    <div>
      <Button
        type="submit"
        :label="t('account.password.change')"
        :loading="saving"
        :disabled="!current || !next || next !== repeat"
      />
    </div>
  </form>
</template>

<style scoped lang="scss">
.section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
</style>
