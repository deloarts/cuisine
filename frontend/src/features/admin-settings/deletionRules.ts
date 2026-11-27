/**
 * The choices of the admin's account deletion dialog and the rules between
 * them, kept apart from the dialog so they are tested on their own. The
 * user's published recipes and ingredients either go to a new owner or stay
 * without one; ownerless recipes keep their visibility, become visible to
 * every signed-in user (public recipes stay public), or are deleted. Private and household recipes cannot keep their
 * visibility without an owner, because nobody could ever see them again.
 * Drafts are always deleted.
 */
import type { Schemas } from '@/core/api/generated'

export type DeletionImpact = Schemas['AccountDeletionImpact']
export type OwnerChoice = 'transfer' | 'nobody'
export type OwnerlessVisibility = 'keep' | 'instance' | 'delete'

export interface DeletionForm {
  owner: OwnerChoice
  newOwnerId: string | null
  visibility: OwnerlessVisibility
}

export interface DeletionQuery {
  new_owner_id?: string
  ownerless_visibility?: OwnerlessVisibility
}

const count = (impact: DeletionImpact, key: string) => impact.recipes[key] ?? 0

/** The user's recipes that are not drafts, over every visibility. */
export function recipeTotal(impact: DeletionImpact): number {
  return Object.values(impact.recipes).reduce((sum, n) => sum + n, 0)
}

/** Private and household recipes, which cannot stay as they are without an owner. */
export function lockedRecipes(impact: DeletionImpact): number {
  return count(impact, 'private') + count(impact, 'household')
}

export function keepAllowed(impact: DeletionImpact): boolean {
  return lockedRecipes(impact) === 0
}

/** Whether there is anything to hand over at all. */
export function needsOwnerChoice(impact: DeletionImpact): boolean {
  return recipeTotal(impact) > 0 || impact.ingredients > 0
}

/** Whether the visibility question applies: nobody takes over and there are recipes. */
export function needsVisibilityChoice(form: DeletionForm, impact: DeletionImpact): boolean {
  return form.owner === 'nobody' && recipeTotal(impact) > 0
}

export function defaultForm(): DeletionForm {
  return { owner: 'transfer', newOwnerId: null, visibility: 'instance' }
}

/** Moves a choice the impact does not allow to the nearest one that is allowed. */
export function normaliseForm(form: DeletionForm, impact: DeletionImpact): DeletionForm {
  const visibility = form.visibility === 'keep' && !keepAllowed(impact) ? 'instance' : form.visibility
  return { ...form, visibility }
}

/**
 * The query for `DELETE /users/{id}`, or null while the form is incomplete
 * (a transfer without a new owner) or chooses what the impact forbids.
 */
export function deletionQuery(form: DeletionForm, impact: DeletionImpact): DeletionQuery | null {
  if (!needsOwnerChoice(impact)) return {}
  if (form.owner === 'transfer') return form.newOwnerId ? { new_owner_id: form.newOwnerId } : null
  if (form.visibility === 'keep' && !keepAllowed(impact)) return null
  return { ownerless_visibility: form.visibility }
}

/** The dialog deletes only once the form is complete and the e-mail address is typed, in any case. */
export function canDelete(form: DeletionForm, impact: DeletionImpact, typed: string, email: string): boolean {
  return deletionQuery(form, impact) !== null && typed.trim().toLowerCase() === email.trim().toLowerCase()
}
