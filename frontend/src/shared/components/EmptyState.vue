<script setup lang="ts">
/**
 * The placeholder for an empty list, table or page, so every empty state
 * announces itself to assistive technology the same way. The default slot
 * takes whatever action helps next, such as a "Create" button.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(defineProps<{ message?: string; icon?: string }>(), {
  message: undefined,
  icon: 'mdi mdi-silverware-fork-knife',
})

const { t } = useI18n()
const displayMessage = computed(() => props.message ?? t('common.empty'))
</script>

<template>
  <div class="empty-state" role="status">
    <i :class="icon" class="empty-state-icon" aria-hidden="true" />
    <p class="empty-state-message">{{ displayMessage }}</p>
    <div v-if="$slots.default" class="empty-state-actions">
      <slot />
    </div>
  </div>
</template>

<style scoped lang="scss">
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-6) var(--space-4);
  text-align: center;
  color: var(--p-text-muted-color);
}

.empty-state-icon {
  font-size: var(--font-size-3xl);
  opacity: 0.6;
}

.empty-state-message {
  font-size: var(--font-size-md);
}

.empty-state-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-1);
}
</style>
