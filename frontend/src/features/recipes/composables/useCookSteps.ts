/**
 * What cook mode shows for each step of the recipe on the stage: its
 * ingredients scaled to the servings, the marks of a variation's changes, and
 * its equipment with what the kitchen lacks. A mirror's lines kept as text go
 * back into the step they belong to: the step itself on the original, the
 * step a variation's step came from. Step mode shows one entry, flow mode all.
 */
import { computed, type Ref } from 'vue'

import type { RecipeDetailResponse, StepMarkerView } from '@/features/recipes/api/recipes'
import { extraIngredients, mergeStepLines, plainEquipmentOf } from '@/features/recipes/utils/mirrors'
import { scaleIngredients } from '@/features/recipes/utils/scaling'
import { lineMarks, markerAt } from '@/features/recipes/utils/variations'

export function useCookSteps(options: {
  recipe: Ref<RecipeDetailResponse | null>
  markers: Ref<StepMarkerView[]>
  variationId: Ref<string | null>
  factor: Ref<number>
  missingIds: Ref<Set<string>>
}) {
  const { recipe, markers, variationId, factor, missingIds } = options
  const mirror = computed(() => recipe.value?.mirror_details ?? null)

  const steps = computed(() =>
    (recipe.value?.steps ?? []).map((step, i) => {
      const marker = markerAt(markers.value, step.position)
      // The source step this one stands for, none for a step a variation added.
      const origin = variationId.value ? marker?.origin_step : i + 1
      const sourceIndex = origin ? origin - 1 : null
      const lines = mergeStepLines(
        step.ingredients,
        mirror.value,
        sourceIndex,
        lineMarks(marker, step.ingredients.length),
      )
      return {
        step,
        ingredients: scaleIngredients(lines.items, factor.value),
        marks: lines.marks,
        equipment: [
          ...step.equipment.map((item) => ({ ...item, missing: missingIds.value.has(item.equipment.id) })),
          ...plainEquipmentOf(mirror.value, sourceIndex),
        ],
      }
    }),
  )

  const allIngredients = computed(() =>
    recipe.value
      ? scaleIngredients([...recipe.value.ingredients, ...extraIngredients(mirror.value)], factor.value)
      : [],
  )

  return { steps, allIngredients }
}

export type CookStepView = ReturnType<typeof useCookSteps>['steps']['value'][number]
