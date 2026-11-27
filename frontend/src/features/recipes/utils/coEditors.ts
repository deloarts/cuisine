/**
 * Who the owner may pick as a co-editor: only people who can read the
 * recipe, judged from its visibility, and never the owner. The backend
 * checks the same and answers 422 otherwise; this keeps the picker from
 * offering people it would refuse. Members of shared groups are not in the
 * group directory, so a shared recipe offers the people it is shared with.
 */
import type { PersonRef, RecipeVisibility } from '@/features/recipes/api/recipes'

export interface CoEditorSources {
  visibility: RecipeVisibility | string
  ownerId: string | null
  everyone: readonly PersonRef[]
  household: readonly PersonRef[]
  sharedUserIds: readonly string[]
}

/** The candidates, household members first, then by name. */
export function coEditorCandidates(sources: CoEditorSources): PersonRef[] {
  const householdIds = new Set(sources.household.map((p) => p.id))
  let pool: readonly PersonRef[]
  switch (sources.visibility) {
    case 'instance':
    case 'peers':
    case 'public':
      pool = sources.everyone
      break
    case 'household':
      pool = sources.household
      break
    case 'shared':
      pool = sources.everyone.filter((p) => sources.sharedUserIds.includes(p.id))
      break
    default:
      pool = []
  }
  const seen = new Set<string>()
  return pool
    .filter((p) => p.id !== sources.ownerId && !seen.has(p.id) && seen.add(p.id))
    .sort(
      (a, b) =>
        Number(householdIds.has(b.id)) - Number(householdIds.has(a.id)) ||
        a.display_name.localeCompare(b.display_name),
    )
}

/** Household members who can be picked and are not picked yet, offered as one-tap suggestions. */
export function coEditorSuggestions(
  candidates: readonly PersonRef[],
  household: readonly PersonRef[],
  chosen: readonly string[],
): PersonRef[] {
  const householdIds = new Set(household.map((p) => p.id))
  return candidates.filter((p) => householdIds.has(p.id) && !chosen.includes(p.id))
}
