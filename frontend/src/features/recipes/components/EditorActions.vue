<script setup lang="ts">
/**
 * The save and cancel actions of an editor page, placed in the page header.
 * On a wide screen every action is its own button, in the given order with
 * the primary one last. Below the small breakpoint they collapse into one
 * split button: the primary action is the main button and the others sit in
 * its menu, so the header stays on one line on a phone.
 */
import type { MenuItem } from 'openvue/menuitem'
import { computed, type ButtonHTMLAttributes } from 'vue'
import { useI18n } from 'vue-i18n'

import { useWideScreen } from '@/shared/composables/useWideScreen'

export interface EditorAction {
  id: string
  label: string
  icon?: string
  primary?: boolean
  // How the action looks as its own button; the primary one keeps the default.
  variant?: 'outlined' | 'text'
  run: () => void
}

const props = defineProps<{
  actions: EditorAction[]
  // Saving or loading: the actions are disabled and the primary one spins.
  busy?: boolean
}>()

const { t } = useI18n()
const wide = useWideScreen()

const primary = computed(() => props.actions.find((a) => a.primary) ?? props.actions[0])
const others = computed<MenuItem[]>(() =>
  props.actions
    .filter((a) => a !== primary.value)
    .map((a) => ({ label: a.label, icon: a.icon, disabled: props.busy, command: () => a.run() })),
)
// Both are bound onto OpenVue buttons, so they may carry the Button's own
// props and test ids next to the plain HTML attributes they are typed as.
const mainButtonProps = computed(
  () => ({ loading: props.busy, 'data-testid': `editor-action-${primary.value?.id}` }) as ButtonHTMLAttributes,
)
const menuButtonProps = computed(
  () => ({ 'aria-label': t('recipes.editor.moreActions'), 'data-testid': 'editor-actions-more' }) as ButtonHTMLAttributes,
)
</script>

<template>
  <div v-if="wide" class="editor-actions">
    <Button
      v-for="action in actions"
      :key="action.id"
      :label="action.label"
      :icon="action.icon"
      :severity="action.primary ? undefined : 'secondary'"
      :outlined="action.variant === 'outlined'"
      :text="action.variant === 'text'"
      :loading="busy && action.primary"
      :disabled="busy"
      :data-testid="`editor-action-${action.id}`"
      @click="action.run()"
    />
  </div>
  <Button
    v-else-if="primary && !others.length"
    :label="primary.label"
    :icon="primary.icon"
    :loading="busy"
    :disabled="busy"
    :data-testid="`editor-action-${primary.id}`"
    @click="primary.run()"
  />
  <SplitButton
    v-else-if="primary"
    :label="primary.label"
    :icon="primary.icon"
    :model="others"
    :disabled="busy"
    :button-props="mainButtonProps"
    :menu-button-props="menuButtonProps"
    @click="primary.run()"
  />
</template>

<style scoped lang="scss">
.editor-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
