<script setup lang="ts">
/**
 * One change of a variation in words: "Honey instead of sugar", "Leave out
 * raisins", or a step's new text. A change that no longer applies says so,
 * and a stale step shows the text the change was written against.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { StaleStepView, VariationChangeView } from '@/features/recipes/api/recipes'
import { useAmountFormat } from '@/features/recipes/composables/useAmountFormat'
import { unitLabel } from '@/features/recipes/utils/scaling'
import RichText from '@/shared/components/richText/RichText.vue'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'

const props = withDefaults(
  defineProps<{ change: VariationChangeView; stale?: StaleStepView | null; showStep?: boolean }>(),
  { stale: null, showStep: false },
)

const { t, locale } = useI18n()
const { format } = useAmountFormat()

function amountText(amount: number | null, unit: VariationChangeView['unit']): string {
  if (amount === null) return ''
  const line = { ingredient_id: null, name: '', amount, unit, note: '' }
  return `${format(amount, contentLocaleOf(locale.value), unit)} ${unitLabel(line)}`.trim()
}

const fallback = '?'
const lineName = computed(
  () => props.change.ingredient_name ?? props.change.sub_recipe?.title ?? t('recipes.subRecipes.hidden'),
)

// The one-line headline of the change; step texts follow below it.
const headline = computed(() => {
  const c = props.change
  switch (c.kind) {
    case 'swap': {
      const amount = c.keep_amount ? '' : amountText(c.amount, c.unit)
      const params = { to: c.to_ingredient_name ?? fallback, from: c.ingredient_name ?? fallback, amount }
      if (amount) return t(c.step === null ? 'recipes.variations.change.swapAmountEverywhere' : 'recipes.variations.change.swapAmount', params)
      return t(c.step === null ? 'recipes.variations.change.swapEverywhere' : 'recipes.variations.change.swap', params)
    }
    case 'add_line': {
      const amount = amountText(c.amount, c.unit)
      return amount
        ? t('recipes.variations.change.addLineAmount', { amount, name: lineName.value })
        : t('recipes.variations.change.addLine', { name: lineName.value })
    }
    case 'remove_line':
      return t('recipes.variations.change.removeLine', { name: lineName.value })
    case 'step_text':
      return t('recipes.variations.change.stepText', { n: c.step ?? 0 })
    default:
      return c.step
        ? t('recipes.variations.change.extraStep', { n: c.step })
        : t('recipes.variations.change.extraStepFirst')
  }
})
const stepLabel = computed(() =>
  props.showStep && props.change.step !== null && ['swap', 'add_line', 'remove_line'].includes(props.change.kind)
    ? t('recipes.variations.change.inStep', { n: props.change.step })
    : '',
)
const ICONS: Record<string, string> = {
  swap: 'mdi-swap-horizontal',
  add_line: 'mdi-plus-circle-outline',
  remove_line: 'mdi-minus-circle-outline',
  step_text: 'mdi-pencil-outline',
  extra_step: 'mdi-playlist-plus',
}
</script>

<template>
  <div class="change" :class="{ 'change--off': !change.available || !change.applies }">
    <p class="change-head">
      <span class="mdi" :class="ICONS[change.kind] ?? 'mdi-circle-small'" aria-hidden="true" />
      <span>
        {{ headline }}
        <span v-if="stepLabel" class="change-step">{{ stepLabel }}</span>
      </span>
    </p>
    <RichText
      v-if="(change.kind === 'step_text' || change.kind === 'extra_step') && change.text"
      class="change-text"
      :text="change.text"
    />
    <ul v-if="change.kind === 'extra_step' && change.lines.length" class="change-lines">
      <li v-for="(line, i) in change.lines" :key="`${line.ingredient_id}-${i}`">
        <strong v-if="line.amount !== null">{{ amountText(line.amount, line.unit) }}</strong>
        {{ line.ingredient_name }}
        <span v-if="line.note" class="change-note">{{ line.note }}</span>
      </li>
    </ul>
    <p v-if="!change.available" class="change-warn">
      <span class="mdi mdi-alert-circle-outline" aria-hidden="true" />
      {{ t('recipes.variations.unavailable') }}
    </p>
    <p v-else-if="!change.applies" class="change-warn">
      <span class="mdi mdi-alert-circle-outline" aria-hidden="true" />
      {{ t('recipes.variations.notApplied') }}
    </p>
    <div v-if="stale" class="change-stale">
      <p class="change-warn">
        <span class="mdi mdi-history" aria-hidden="true" />
        {{ stale.state === 'deleted' ? t('recipes.variations.staleDeleted') : t('recipes.variations.stale') }}
      </p>
      <p class="change-stale-label">{{ t('recipes.variations.staleWas') }}</p>
      <RichText class="change-stale-text" :text="stale.old_text" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.change {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.change-head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-weight: 700;

  .mdi {
    color: var(--p-primary-color);
    font-size: var(--font-size-lg);
    line-height: 1.3;
  }
}

.change-step {
  color: var(--p-text-muted-color);
  font-weight: 400;
}

.change--off .change-head {
  color: var(--p-text-muted-color);
  text-decoration: line-through;
}

.change-text {
  padding-left: var(--space-5);
}

.change-lines {
  margin: 0;
  padding-left: var(--space-6);
}

.change-note {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.change-warn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-orange-700);
  font-size: var(--font-size-sm);
}

.p-dark .change-warn {
  color: var(--p-orange-400);
}

.change-stale {
  padding: var(--space-2) var(--space-3);
  border-left: 3px solid var(--p-orange-400);
  background: var(--p-surface-50);
  border-radius: 0 var(--p-border-radius-md) var(--p-border-radius-md) 0;
}

.p-dark .change-stale {
  background: var(--p-surface-900);
}

.change-stale-label {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.change-stale-text {
  color: var(--p-text-muted-color);
}
</style>
