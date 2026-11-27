<script setup lang="ts">
/**
 * The browse filters for who is eating: the diets every recipe must fit,
 * and the dinner guests whose restrictions count. For guests the backend
 * only says whether someone won't like a recipe, never who or why, and only
 * for guests who allowed it.
 */
import { useI18n } from 'vue-i18n'

import { DIETS } from '@/shared/components/recipes/dietBadge'
import UserPicker from '@/shared/cookbook/UserPicker.vue'

const diets = defineModel<string[]>('diets', { required: true })
const guests = defineModel<string[]>('guests', { required: true })
const hideUnsuitable = defineModel<boolean>('hideUnsuitable', { required: true })

const { t } = useI18n()

function toggleDiet(diet: string) {
  diets.value = diets.value.includes(diet)
    ? diets.value.filter((d) => d !== diet)
    : [...diets.value, diet]
}
</script>

<template>
  <div class="diet-guests">
    <fieldset class="diet-guests-group">
      <legend class="field-label">{{ t('recipes.diets.label') }}</legend>
      <div class="diet-chips">
        <button
          v-for="diet in DIETS"
          :key="diet"
          type="button"
          class="diet-chip"
          :class="{ 'diet-chip--on': diets.includes(diet) }"
          :aria-pressed="diets.includes(diet)"
          @click="toggleDiet(diet)"
        >
          {{ t(`diets.${diet}`) }}
        </button>
      </div>
      <small class="field-hint">{{ t('recipes.diets.hint') }}</small>
    </fieldset>

    <div class="diet-guests-group">
      <span id="guest-picker-label" class="field-label">{{ t('recipes.guests.label') }}</span>
      <UserPicker v-model="guests" input-id="guest-picker" labelledby="guest-picker-label" />
      <div class="guest-hide">
        <ToggleSwitch
          v-model="hideUnsuitable"
          input-id="guest-hide"
          :disabled="guests.length === 0"
        />
        <label for="guest-hide">{{ t('recipes.guests.hide') }}</label>
      </div>
      <small class="field-hint">
        {{ t('recipes.guests.hint') }}
        <template v-if="guests.length === 1">{{ t('recipes.guests.singleHint') }}</template>
      </small>
    </div>
  </div>
</template>

<style scoped lang="scss">
.diet-guests {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.diet-guests-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
  margin: 0;
  padding: 0;
  border: none;
}

.diet-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.diet-chip {
  display: inline-flex;
  align-items: center;
  min-height: 2.75rem;
  padding: 0 var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: 2rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  cursor: pointer;

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  }
}

.diet-chip--on {
  border-color: var(--p-primary-color);
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
}

.guest-hide {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

@media (min-width: $bp-md) {
  .diet-guests {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--space-5);
  }
}
</style>
