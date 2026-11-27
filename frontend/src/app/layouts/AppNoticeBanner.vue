<script setup lang="ts">
/**
 * The admin's in-app banner, under the header for every signed-in user.
 * It shows only inside its time window, and a closable banner stays closed
 * on this device until its text changes (the key changes with it).
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { getBanner, type PublicBanner } from '@/shared/api/notices'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { safeStorage } from '@/core/utils/safeStorage'

const DISMISSED_KEY = 'bannerDismissed'

const { t, locale } = useI18n()
const banner = ref<PublicBanner | null>(null)
const dismissed = ref(safeStorage.get(DISMISSED_KEY))

const visible = computed(() => {
  const b = banner.value
  if (!b || !b.message.trim()) return false
  if (b.ends_at && new Date(b.ends_at) < new Date()) return false
  return !(b.dismissible && dismissed.value === b.key)
})
const severity = computed(() => {
  if (banner.value?.severity === 'critical') return 'error'
  return banner.value?.severity === 'warning' ? 'warn' : 'info'
})

async function load() {
  try {
    banner.value = await getBanner(contentLocaleOf(locale.value))
  } catch {
    banner.value = null
  }
}

function dismiss() {
  if (!banner.value) return
  dismissed.value = banner.value.key
  safeStorage.set(DISMISSED_KEY, banner.value.key)
}

watch(locale, () => void load())
onMounted(() => void load())
</script>

<template>
  <div v-if="visible && banner" class="notice-banner">
    <Message :severity="severity" :closable="banner.dismissible" :close-button-props="{ 'aria-label': t('common.close') }" @close="dismiss">
      {{ banner.message }}
    </Message>
  </div>
</template>

<style scoped lang="scss">
.notice-banner {
  padding: var(--space-1) var(--space-2);
}
</style>
