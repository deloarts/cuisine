<script setup lang="ts">
/**
 * The maintenance notice under the header: while the admin or the upgrade
 * sidecar keeps the instance read-only, everyone sees why their changes are
 * refused. It checks again every minute, since maintenance can start while
 * the app is open.
 */
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { useMaintenance } from '@/shared/maintenance/useMaintenance'

const POLL_MS = 60_000

const { t, locale } = useI18n()
const { maintenance, refresh } = useMaintenance()
let timer: ReturnType<typeof setInterval> | undefined

const load = () => void refresh(contentLocaleOf(locale.value))

watch(locale, load)
onMounted(() => {
  load()
  timer = setInterval(load, POLL_MS)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div v-if="maintenance?.enabled" class="maintenance-banner" role="status">
    <Message severity="warn" icon="mdi mdi-wrench-clock" :closable="false">
      <strong>{{ t('maintenance.title') }}</strong>
      {{ maintenance.message || t('maintenance.fallback') }}
    </Message>
  </div>
</template>

<style scoped lang="scss">
.maintenance-banner {
  padding: var(--space-1) var(--space-2);
}
</style>
