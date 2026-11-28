<script setup lang="ts">
/**
 * One step in cook mode, in type large enough to read from a step away: its
 * number, its text with the amounts filled in, its photo, a timer button when
 * it has a duration, and the ingredients and equipment it needs. Step mode
 * shows one at a time; flow mode lists all of them, highlights the current
 * one and lets a tap on the number make a step current.
 */
import { useI18n } from 'vue-i18n'

import EquipmentList from '@/features/recipes/components/EquipmentList.vue'
import IngredientLines from '@/features/recipes/components/IngredientLines.vue'
import { useAmountFormat } from '@/features/recipes/composables/useAmountFormat'
import type { CookStepView } from '@/features/recipes/composables/useCookSteps'
import { lineResolver } from '@/features/recipes/utils/mentionResolver'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { imageUrl } from '@/shared/components/recipes/recipeImage'
import RichText from '@/shared/components/richText/RichText.vue'

const props = withDefaults(
  defineProps<{
    view: CookStepView
    number: number
    // Whether the session timer already counts for this step.
    timing?: boolean
    // Flow mode: the step is the current one, and the number selects it.
    current?: boolean
    selectable?: boolean
  }>(),
  { timing: false, current: false, selectable: false },
)
const emit = defineEmits<{ startTimer: []; select: [] }>()

const { t, locale } = useI18n()
const { style: amountStyle } = useAmountFormat()
</script>

<template>
  <section class="cook-step" :class="{ 'cook-step--current': props.current }" :aria-current="props.current ? 'step' : undefined">
    <button
      v-if="props.selectable"
      type="button"
      class="cook-step-number"
      :aria-label="t('recipes.cookMode.goToStep', { n: props.number })"
      @click="emit('select')"
    >
      {{ props.number }}
    </button>
    <div v-else class="cook-step-number" aria-hidden="true">{{ props.number }}</div>
    <RichText
      class="cook-step-text"
      :text="props.view.step.text"
      :resolve="
        lineResolver(props.view.ingredients, {
          amounts: true,
          locale: contentLocaleOf(locale),
          amountStyle,
          hiddenName: t('recipes.subRecipes.hidden'),
          equipment: props.view.step.equipment,
        })
      "
    />
    <img v-if="props.view.step.image_id" :src="imageUrl(props.view.step.image_id, 'original')" alt="" class="cook-image" />
    <div v-if="props.view.step.duration_minutes && !props.timing" class="cook-timer-start">
      <Button
        :label="t('recipes.cookMode.startTimer', { m: props.view.step.duration_minutes })"
        icon="mdi mdi-timer-outline"
        severity="secondary"
        outlined
        size="large"
        @click="emit('startTimer')"
      />
    </div>
    <div v-if="props.view.ingredients.length" class="cook-needs">
      <h2>{{ t('recipes.cookMode.ingredients') }}</h2>
      <IngredientLines :items="props.view.ingredients" :marks="props.view.marks" large />
    </div>
    <div v-if="props.view.equipment.length" class="cook-needs" data-testid="cook-step-equipment">
      <h2>{{ t('recipes.cookMode.equipment') }}</h2>
      <EquipmentList :items="props.view.equipment" large />
    </div>
  </section>
</template>

<style scoped lang="scss">
.cook-step {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cook-step-number {
  display: grid;
  place-items: center;
  width: 3.5rem;
  height: 3.5rem;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  font: inherit;
  font-weight: 800;
  font-size: var(--font-size-2xl);
}

button.cook-step-number {
  cursor: pointer;

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
    outline-offset: 2px;
  }
}

// The step text is what the cook reads from a step away, so it scales with
// the screen instead of sitting at body size.
.cook-step-text {
  font-size: clamp(1.4rem, 5.5vw, 2.25rem);
  line-height: 1.45;
}

.cook-image {
  width: 100%;
  max-height: 40vh;
  object-fit: cover;
  border-radius: var(--p-border-radius-lg);
}

.cook-needs {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-surface-50);

  h2 {
    font-family: var(--font-head);
    font-weight: 700;
    font-size: var(--font-size-md);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--p-text-muted-color);
  }
}

.p-dark .cook-needs {
  background: var(--p-surface-900);
}
</style>
