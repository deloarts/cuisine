<script setup lang="ts">
/**
 * Shows an imprint or privacy statement written in Markdown. The renderer
 * escapes every HTML tag, so v-html only receives markup it produced itself.
 */
import { computed } from 'vue'

import { renderLegalMarkdown } from '@/shared/components/legal/legalMarkdown'

const props = defineProps<{ text: string | null | undefined }>()
const html = computed(() => renderLegalMarkdown(props.text))
</script>

<template>
  <!-- v-html: renderLegalMarkdown escapes all HTML (legalMarkdown.ts). -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="legal-text" v-html="html" />
</template>

<style scoped lang="scss">
.legal-text {
  overflow-wrap: anywhere;
  line-height: 1.6;

  :deep(h1),
  :deep(h2),
  :deep(h3) {
    margin: var(--space-4) 0 var(--space-2);
    font-family: var(--font-head);
    font-weight: 700;
  }

  :deep(h1) {
    font-size: var(--font-size-2xl);
  }

  :deep(h2) {
    font-size: var(--font-size-xl);
  }

  :deep(h3) {
    font-size: var(--font-size-lg);
  }

  :deep(p),
  :deep(ul),
  :deep(ol) {
    margin: 0 0 var(--space-2);
  }

  :deep(a) {
    color: var(--p-primary-color);
  }
}
</style>
