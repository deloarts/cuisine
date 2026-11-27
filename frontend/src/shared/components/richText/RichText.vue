<script setup lang="ts">
/**
 * Shows recipe text written in the Markdown subset of `markdown.ts`. The
 * renderer escapes every HTML tag, so v-html only ever receives markup it
 * produced itself from the subset. `resolve` gives mentions their current
 * name, an amount in cook mode and the sub-recipe to link to; such a link
 * opens through the router. `plainMentions` shows mentions as normal text
 * for readers who turned the highlighting off, while a sub-recipe link keeps
 * its underline so it still reads as a link.
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { renderMarkdown, type MentionResolver } from '@/shared/components/richText/markdown'

const props = withDefaults(
  defineProps<{ text: string | null | undefined; resolve?: MentionResolver | null; plainMentions?: boolean }>(),
  { resolve: null, plainMentions: false },
)
const router = useRouter()
const html = computed(() => renderMarkdown(props.text, props.resolve ?? undefined))

function follow(event: MouseEvent) {
  const link = (event.target as HTMLElement | null)?.closest<HTMLElement>('a[data-recipe-id]')
  if (!link?.dataset.recipeId) return
  event.preventDefault()
  void router.push({ name: 'recipe', params: { id: link.dataset.recipeId } })
}
</script>

<template>
  <!-- v-html: renderMarkdown escapes all HTML (markdown.ts). The click handler only catches
       clicks bubbling from the sub-recipe links inside, which are keyboard reachable themselves. -->
  <!-- eslint-disable-next-line vue/no-v-html, vuejs-accessibility/click-events-have-key-events, vuejs-accessibility/no-static-element-interactions -->
  <div class="rich-text" :class="{ 'rich-text--plain-mentions': plainMentions }" @click="follow" v-html="html" />
</template>

<style scoped lang="scss">
.rich-text {
  overflow-wrap: anywhere;

  :deep(p) {
    margin: 0 0 0.6em;
  }

  :deep(ul),
  :deep(ol) {
    margin: 0 0 0.6em;
    padding-left: 1.4em;
  }

  :deep(li) {
    margin-bottom: 0.2em;
  }

  > :deep(:last-child) {
    margin-bottom: 0;
  }

  // The padding is taken back by a negative margin, so a word that goes on
  // after the mention ("Salz" + "en") reads as one word.
  :deep(.mention) {
    margin-inline: -0.12em;
    padding: 0 0.12em;
    border-radius: var(--p-border-radius-sm);
    background: var(--p-highlight-background);
    color: var(--p-highlight-color);
    font-weight: 700;
  }

  :deep(a.mention) {
    text-decoration: underline;
  }
}

.rich-text--plain-mentions :deep(.mention) {
  margin-inline: 0;
  padding: 0;
  background: none;
  color: inherit;
  font-weight: inherit;
}
</style>
