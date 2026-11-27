<script setup lang="ts">
/**
 * Equipment as the recipe page and cook mode list it: icon, count and name,
 * the step's note, and a mark on an item the reader's kitchen lacks.
 */
import { useI18n } from 'vue-i18n'

import { equipmentLabel } from '@/features/recipes/utils/equipment'
import { equipmentIcon } from '@/shared/cookbook/equipment'
import type { EquipmentRef } from '@/shared/cookbook/types'

export interface EquipmentLine {
  equipment: EquipmentRef
  count: number | null
  note?: string
  missing?: boolean | null
}

withDefaults(defineProps<{ items: EquipmentLine[]; large?: boolean }>(), { large: false })
const { t } = useI18n()
</script>

<template>
  <ul class="equipment" :class="{ 'equipment--large': large }">
    <li
      v-for="item in items"
      :key="item.equipment.id"
      class="equipment-item"
      :class="{ 'equipment-item--missing': item.missing === true }"
      :data-testid="`equipment-${item.equipment.id}`"
    >
      <span :class="equipmentIcon(item.equipment.icon)" class="equipment-icon" aria-hidden="true" />
      <span class="equipment-name">
        {{ equipmentLabel(item.equipment.name, item.count) }}
        <span v-if="item.note" class="equipment-note">{{ item.note }}</span>
      </span>
      <span v-if="item.missing === true" class="equipment-missing">
        <span class="mdi mdi-alert-circle-outline" aria-hidden="true" />
        {{ t('recipes.equipment.missing') }}
      </span>
    </li>
  </ul>
</template>

<style scoped lang="scss">
.equipment {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.equipment-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-2);
  min-height: 2rem;
}

.equipment-icon {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-lg);
}

.equipment-name {
  flex: 1;
  min-width: 0;
}

.equipment-note {
  margin-left: var(--space-1);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.equipment-missing {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-orange-600);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.p-dark .equipment-missing {
  color: var(--p-orange-400);
}

.equipment--large {
  gap: var(--space-2);
  font-size: clamp(1.1rem, 4vw, 1.35rem);

  .equipment-icon {
    font-size: var(--font-size-2xl);
  }
}
</style>
