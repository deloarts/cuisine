/**
 * What the editors' unit pickers need to say whether a line's amount can be
 * weighed: each line ingredient's density and own conversions. An ingredient
 * picked in this session is remembered from the search result; one already on
 * a loaded recipe is fetched once and kept for the rest of the session, since
 * these values do not depend on the language.
 */
import { reactive } from 'vue'

import { getIngredient } from '@/features/recipes/api/editorSupport'
import type { WeighableIngredient } from '@/shared/cookbook/units'

const known = reactive(new Map<string, WeighableIngredient>())
const loading = new Set<string>()

function remember(id: string, ingredient: WeighableIngredient) {
  known.set(id, { density_g_per_ml: ingredient.density_g_per_ml, conversions: ingredient.conversions })
}

/** Starts loading an ingredient's weights; a failed load leaves it unknown, so the picker shows no hint. */
function load(id: string) {
  if (known.has(id) || loading.has(id)) return
  loading.add(id)
  void getIngredient(id)
    .then((detail) => remember(id, detail))
    .catch(() => undefined)
    .finally(() => loading.delete(id))
}

export function useIngredientWeights() {
  /** The weights of an ingredient, or null while they are unknown; asking starts the load. */
  function weightsOf(id: string | null | undefined): WeighableIngredient | null {
    if (!id) return null
    const found = known.get(id)
    if (!found) load(id)
    return found ?? null
  }

  return { weightsOf, remember }
}
