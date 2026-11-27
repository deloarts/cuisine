<script setup lang="ts">
/**
 * The `@` suggestions under the cursor: ingredients, recipes and equipment,
 * the arrow keys move through them and Enter picks one. A suggestion found by
 * another of its names shows that name first ("Tomate → Paradeiser"). The
 * editor forwards its key presses through `onKeyDown`.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { MentionRef } from '@/shared/components/richText/mentions'

const props = defineProps<{ items: MentionRef[]; command: (item: MentionRef) => void }>()
const { t } = useI18n()
const active = ref(0)

const ICONS: Record<MentionRef['kind'], string> = {
  ingredient: 'mdi-food-apple-outline',
  recipe: 'mdi-book-open-page-variant-outline',
  equipment: 'mdi-pot-mix-outline',
}

watch(
  () => props.items,
  () => (active.value = 0),
)

function pick(index: number) {
  const item = props.items[index]
  if (item) props.command(item)
}

function onKeyDown(event: KeyboardEvent): boolean {
  const count = props.items.length
  if (!count) return false
  if (event.key === 'ArrowDown') {
    active.value = (active.value + 1) % count
    return true
  }
  if (event.key === 'ArrowUp') {
    active.value = (active.value + count - 1) % count
    return true
  }
  if (event.key === 'Enter' || event.key === 'Tab') {
    pick(active.value)
    return true
  }
  return false
}

defineExpose({ onKeyDown })
</script>

<template>
  <div class="mention-list" role="listbox" :aria-label="t('richText.mentionSuggestions')">
    <p v-if="items.length === 0" class="mention-list-empty">{{ t('richText.mentionEmpty') }}</p>
    <button
      v-for="(item, i) in items"
      :key="`${item.kind}-${item.id}`"
      type="button"
      role="option"
      class="mention-list-item"
      :class="{ 'mention-list-item--active': i === active }"
      :aria-selected="i === active"
      @mousedown.prevent="pick(i)"
    >
      <span class="mdi" :class="ICONS[item.kind]" aria-hidden="true" />
      <span class="mention-list-name">
        <template v-if="item.alias">
          <span class="mention-list-alias">{{ item.alias }}</span>
          <span aria-hidden="true"> → </span>
          <span class="visually-hidden">{{ t('recipes.editor.mentionAliasOf') }}</span>
        </template>
        {{ item.name }}
      </span>
      <small v-if="item.kind === 'recipe'" class="mention-list-kind">{{ t('recipes.subRecipes.recipe') }}</small>
      <small v-else-if="item.kind === 'equipment'" class="mention-list-kind">
        {{ t('recipes.equipment.mentionKind') }}
      </small>
    </button>
  </div>
</template>

<style scoped lang="scss">
.mention-list {
  display: flex;
  flex-direction: column;
  min-width: 14rem;
  max-width: min(22rem, 90vw);
  max-height: 16rem;
  overflow-y: auto;
  padding: var(--space-1);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  background: var(--p-content-background);
  box-shadow: var(--shadow-lg);
}

.mention-list-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  padding: 0 var(--space-2);
  border: none;
  border-radius: var(--p-border-radius-sm);
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.mention-list-item--active {
  background: var(--p-highlight-background);
  color: var(--p-highlight-color);
}

.mention-list-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.mention-list-alias {
  font-style: italic;
}

.mention-list-kind,
.mention-list-empty {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.mention-list-empty {
  padding: var(--space-2);
}
</style>
