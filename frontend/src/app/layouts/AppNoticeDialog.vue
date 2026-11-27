<script setup lang="ts">
/**
 * Shows the admin's dialog notices this user has not confirmed yet, one
 * after the other, right after the app loads. A notice closes only through
 * its confirm button, which records the acknowledgement.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import RichText from '@/shared/components/richText/RichText.vue'
import { acknowledgeNotice, getPendingNotices, type PendingNotice } from '@/shared/api/notices'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { useAppToast } from '@/core/composables/useAppToast'

const { t, locale } = useI18n()
const toast = useAppToast()
const pending = ref<PendingNotice[]>([])
const confirming = ref(false)

const current = computed(() => pending.value[0] ?? null)
const visible = computed(() => current.value !== null)

async function load() {
  try {
    pending.value = await getPendingNotices(contentLocaleOf(locale.value))
  } catch {
    pending.value = []
  }
}

async function confirm() {
  const notice = current.value
  if (!notice) return
  confirming.value = true
  try {
    await acknowledgeNotice(notice.id)
    pending.value = pending.value.slice(1)
  } catch (err) {
    toast.error(err)
  } finally {
    confirming.value = false
  }
}

watch(locale, () => void load())
onMounted(() => void load())
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :closable="false"
    :close-on-escape="false"
    :header="current?.title"
    class="notice-dialog"
  >
    <RichText :text="current?.body" />
    <template #footer>
      <Button :label="t('notices.confirm')" icon="mdi mdi-check" :loading="confirming" @click="confirm" />
    </template>
  </Dialog>
</template>

<style scoped lang="scss">
.notice-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}
</style>
