<script setup lang="ts">
/**
 * A list of ingredients with their amounts, as the recipe page and cook mode
 * show them. With `marks`, a line a variation swapped or added is
 * highlighted. On a mirror, a line this instance keeps as text says so, and
 * a sub-recipe that is not on this instance shows as a placeholder. With
 * `compact`, as inside a step, the amount column is only as wide as the
 * longest amount, the rows sit closer together, and the note and the
 * variation mark follow the name on the same line.
 */
import { useI18n } from 'vue-i18n'

import { contentLocaleOf } from '@/shared/cookbook/contentLocale'

import type { ShownLine } from '@/features/recipes/utils/mirrors'
import { useAmountFormat } from '@/features/recipes/composables/useAmountFormat'
import { unitLabel } from '@/features/recipes/utils/scaling'
import type { LineMark } from '@/features/recipes/utils/variations'

withDefaults(
  defineProps<{
    items: ShownLine[]
    large?: boolean
    compact?: boolean
    warnIds?: string[]
    marks?: (LineMark | null)[]
  }>(),
  { large: false, compact: false, warnIds: () => [], marks: () => [] },
)
const { t, locale } = useI18n()
const numberLocale = () => contentLocaleOf(locale.value)
const { format } = useAmountFormat()
const lineKey = (item: ShownLine, i: number) =>
  `${item.ingredient_id ?? item.sub_recipe?.id ?? item.origin ?? 'hidden'}-${item.unit?.id ?? ''}-${i}`
const warned = (item: ShownLine, ids: string[]) =>
  item.ingredient_id !== null && ids.includes(item.ingredient_id)
</script>

<template>
  <ul class="lines" :class="{ 'lines--large': large, 'lines--compact': compact }">
    <li
      v-for="(item, i) in items"
      :key="lineKey(item, i)"
      class="line"
      :class="{ 'line--warn': warned(item, warnIds), 'line--marked': !!marks[i] }"
    >
      <span class="line-amount">
        <template v-if="item.amount !== null">
          {{ format(item.amount, numberLocale(), item.unit) }} {{ unitLabel(item) }}
        </template>
        <span v-else class="line-taste">{{ t('recipes.detail.toTaste') }}</span>
      </span>
      <span class="line-name">
        <span v-if="item.origin === 'unlinked'" class="line-hidden" data-testid="line-unlinked">
          <span class="mdi mdi-book-open-page-variant-outline" aria-hidden="true" />
          {{ item.name ? t('recipes.mirror.unlinkedNamed', { title: item.name }) : t('recipes.mirror.unlinked') }}
        </span>
        <template v-else-if="item.sub_recipe">
          <RouterLink
            v-if="item.sub_recipe.accessible && item.sub_recipe.id"
            :to="{ name: 'recipe', params: { id: item.sub_recipe.id } }"
            class="line-recipe"
          >
            <span class="mdi mdi-book-open-page-variant-outline" aria-hidden="true" />
            {{ item.sub_recipe.title }}
          </RouterLink>
          <span v-else class="line-hidden">{{ t('recipes.subRecipes.hidden') }}</span>
        </template>
        <template v-else>{{ item.name }}</template>
        <span v-if="item.note" class="line-note">{{ item.note }}</span>
        <span
          v-if="item.origin === 'plain'"
          class="line-plain"
          :title="t('recipes.mirror.plainLineHint')"
          data-testid="line-plain"
        >
          {{ t('recipes.mirror.plainLine') }}
        </span>
        <span v-if="marks[i]" class="line-mark">
          <span class="mdi mdi-source-branch" aria-hidden="true" />
          {{
            marks[i]!.kind === 'swapped' && marks[i]!.from
              ? t('recipes.variations.swappedFrom', { name: marks[i]!.from })
              : t('recipes.variations.addedLine')
          }}
        </span>
        <span
          v-if="warned(item, warnIds)"
          class="mdi mdi-alert-circle line-warn-icon"
          :title="t('recipes.card.warning')"
          aria-hidden="true"
        />
      </span>
    </li>
  </ul>
</template>

<style scoped lang="scss">
.lines {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.line {
  display: grid;
  grid-template-columns: minmax(4.5rem, 30%) 1fr;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--p-content-border-color);

  &:last-child {
    border-bottom: none;
  }
}

.line-amount {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

// "To taste" is a hint rather than an amount: lighter, and small enough to
// stay on one line in the narrow amount column.
.line-taste {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
  font-weight: 400;
  white-space: nowrap;
}

.line-note {
  display: block;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.line-recipe {
  color: var(--p-primary-color);
  font-weight: 700;
}

.line-hidden {
  color: var(--p-text-muted-color);
  font-style: italic;
}

.line-plain {
  display: block;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xs);
}

.line--warn .line-name {
  color: var(--p-orange-700);
}

.line--marked {
  border-left: 3px solid var(--p-primary-color);
  padding-left: var(--space-2);
}

.line-mark {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-primary-color);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.line-warn-icon {
  margin-left: var(--space-1);
}

.lines--large {
  font-size: clamp(1.15rem, 4.5vw, 1.6rem);

  .line {
    padding: var(--space-3) 0;
  }

  .line-note {
    font-size: 0.75em;
  }
}

// The rows share one amount column through a subgrid, so the amounts still
// line up while the column shrinks to the widest of them.
.lines--compact {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  column-gap: var(--space-3);

  .line {
    grid-column: 1 / -1;
    grid-template-columns: subgrid;
    padding: var(--space-1) 0;
  }

  // Each ingredient keeps to one line in a step: the note and the variation
  // mark follow the name instead of stacking under it, and a changed line
  // goes without its own bar, since the step box already has one.
  .line-name {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    column-gap: var(--space-2);
  }

  .line-note,
  .line-plain {
    display: inline;
  }

  .line--marked {
    border-left: none;
    padding-left: 0;
  }
}
</style>
