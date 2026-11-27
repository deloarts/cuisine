<script setup lang="ts">
/**
 * One equipment item as a suggestion row of a picker: its icon and name,
 * led by the other name the search matched ("Schneebesen → Rührbesen").
 */
import { useI18n } from 'vue-i18n'

import { equipmentIcon } from './equipment'

defineProps<{ name: string; icon?: string | null; alias?: string | null }>()

const { t } = useI18n()
</script>

<template>
  <span class="equipment-option">
    <span :class="equipmentIcon(icon)" aria-hidden="true" />
    <span>
      <template v-if="alias">
        <em>{{ alias }}</em>
        <span aria-hidden="true"> → </span>
        <span class="visually-hidden">{{ t('pickers.aliasOf') }}</span>
      </template>
      {{ name }}
    </span>
  </span>
</template>

<style scoped lang="scss">
.equipment-option {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
