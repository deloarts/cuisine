<script setup lang="ts">
/** The servings stepper that scales every amount on the recipe page and in cook mode. */
import { useI18n } from 'vue-i18n'

const servings = defineModel<number>({ required: true })
const props = withDefaults(defineProps<{ min?: number; max?: number }>(), { min: 1, max: 99 })
const { t } = useI18n()

function change(delta: number) {
  servings.value = Math.max(props.min, Math.min(props.max, servings.value + delta))
}
</script>

<template>
  <div class="stepper" role="group" :aria-label="t('recipes.servings.label')">
    <Button
      icon="mdi mdi-minus"
      rounded
      outlined
      severity="secondary"
      :disabled="servings <= min"
      :aria-label="t('recipes.servings.decrease')"
      @click="change(-1)"
    />
    <span class="stepper-value" aria-live="polite">
      {{ t('recipes.servings.count', { n: servings }, servings) }}
    </span>
    <Button
      icon="mdi mdi-plus"
      rounded
      outlined
      severity="secondary"
      :disabled="servings >= max"
      :aria-label="t('recipes.servings.increase')"
      @click="change(1)"
    />
  </div>
</template>

<style scoped lang="scss">
.stepper {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
}

.stepper-value {
  min-width: 6.5rem;
  text-align: center;
  font-weight: 700;
}
</style>
