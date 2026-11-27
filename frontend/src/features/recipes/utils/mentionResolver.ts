/**
 * Gives the mentions of a step their current name from the step's lines and
 * equipment, which the backend resolves in the reader's language, and in
 * cook mode the scaled amount ("300 g Flour"). A sub-recipe the reader
 * cannot open keeps no link.
 */
import type { IngredientAmount, StepView } from '@/features/recipes/api/recipes'
import { type AmountStyle, formatAmount, unitLabel } from '@/features/recipes/utils/scaling'
import type { MentionDisplay, MentionResolver } from '@/shared/components/richText/markdown'

export function lineResolver(
  lines: IngredientAmount[],
  options: {
    amounts?: boolean
    locale?: string
    // How the reader wants small metric amounts, see `formatAmount`.
    amountStyle?: AmountStyle
    hiddenName?: string
    equipment?: StepView['equipment']
  } = {},
): MentionResolver {
  return (ref) => {
    if (ref.kind === 'equipment') {
      const item = options.equipment?.find((e) => e.equipment.id === ref.id)
      return item ? { name: item.equipment.name } : null
    }
    const line = lines.find((l) =>
      ref.kind === 'recipe' ? l.sub_recipe?.id === ref.id : l.ingredient_id === ref.id,
    )
    if (!line) return null
    const shown: MentionDisplay =
      ref.kind === 'recipe'
        ? line.sub_recipe?.accessible
          ? { name: line.sub_recipe.title ?? ref.name, recipeId: line.sub_recipe.id }
          : { name: options.hiddenName ?? ref.name, recipeId: null }
        : { name: line.name }
    if (options.amounts && line.amount !== null) {
      shown.amount = `${formatAmount(line.amount, options.locale ?? 'en-GB', line.unit?.kind, {
        style: options.amountStyle,
        unitCode: line.unit?.code,
      })} ${unitLabel(line)}`.trim()
    }
    return shown
  }
}
