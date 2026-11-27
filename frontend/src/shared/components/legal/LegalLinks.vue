<script setup lang="ts">
/**
 * Links to the imprint and the privacy statement, each only once the
 * administrator has published it. The shell's footer and the sign-in page
 * show them; the parent styles the links.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { usePublicInfoStore } from '@/core/stores/publicInfoStore'

const { t } = useI18n()
const publicInfo = usePublicInfoStore()

const links = computed(() => {
  const info = publicInfo.info
  if (!info) return []
  return [
    ...(info.imprint_published ? [{ kind: 'imprint', label: t('legal.imprint') }] : []),
    ...(info.privacy_statement_published ? [{ kind: 'privacy', label: t('legal.privacy') }] : []),
  ]
})
</script>

<template>
  <nav v-if="links.length" class="legal-links" :aria-label="t('legal.links')">
    <RouterLink v-for="link in links" :key="link.kind" :to="{ name: 'legal', params: { kind: link.kind } }">
      {{ link.label }}
    </RouterLink>
  </nav>
</template>

<style scoped lang="scss">
.legal-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-1) var(--space-4);
  font-size: var(--font-size-sm);

  a {
    display: inline-flex;
    align-items: center;
    min-height: 2.75rem;
  }
}
</style>
