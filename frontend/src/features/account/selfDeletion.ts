/**
 * The rules of deleting the own account, apart from the dialog so they are
 * tested on their own. The impact comes from the backend, computed for this
 * user and this instance: what stays online, what is handed over, what is
 * deleted. The one choice is whether the recipes that would stay online are
 * deleted too, offered only when the instance lets users choose visibility.
 * Deleting needs a re-authentication (password or passkey) and the typed
 * e-mail address, and the backend refuses the system user and the last admin.
 */
import type { Schemas } from '@/core/api/generated'

export type SelfDeletionImpact = Schemas['SelfDeletionImpact']
export type SelfDeletionRequest = Schemas['SelfDeletionRequest']
export type PasskeyConfirmation = Schemas['PasskeyConfirmation']
export type HandedOverRecipe = Schemas['HandedOverRecipe']

export interface ImpactLine {
  key: string
  count: number
  /** The recipes another user's recipe uses, each with its new owner. */
  recipes?: HandedOverRecipe[]
}

export interface ImpactSummary {
  staysOnline: ImpactLine[]
  handedOver: ImpactLine[]
  deleted: ImpactLine[]
}

export interface SelfDeletionForm {
  deletePublic: boolean
  password: string
  passkey: PasskeyConfirmation | null
  typed: string
}

export function emptyForm(): SelfDeletionForm {
  return { deletePublic: false, password: '', passkey: null, typed: '' }
}

export function refused(impact: SelfDeletionImpact): boolean {
  return impact.refused_reason !== null
}

/** Whether the dialog offers "delete my public recipes too". */
export function offersPublicDeletion(impact: SelfDeletionImpact): boolean {
  return impact.can_delete_public_recipes && impact.recipes_kept_online > 0
}

function lines(entries: [string, number][]): ImpactLine[] {
  return entries.filter(([, count]) => count > 0).map(([key, count]) => ({ key, count }))
}

/** The impact sorted into the three groups the dialog lists, given the choice. */
export function summarise(impact: SelfDeletionImpact, deletePublic: boolean): ImpactSummary {
  // Deleting the public recipes changes the fates of the recipes below them too.
  const chosen = deletePublic && offersPublicDeletion(impact) ? impact.if_public_deleted : null
  const fates = chosen ?? impact
  return {
    staysOnline: lines([
      ['recipesOnline', chosen ? 0 : impact.recipes_kept_online],
      ['subRecipesKept', fates.sub_recipes_kept_online],
      ['ingredientsKept', impact.ingredients_kept],
    ]),
    handedOver: [
      ...lines([['recipesToHousehold', impact.recipes_to_household]]),
      ...lines([['recipesHandedOver', fates.recipes_handed_over.length]]).map((line) => ({
        ...line,
        recipes: fates.recipes_handed_over,
      })),
      ...lines([['listsHandedOver', impact.lists_handed_over]]),
    ],
    deleted: lines([
      ['recipesDeleted', fates.recipes_deleted],
      ['draftsDeleted', fates.drafts_deleted],
      ['listsDeleted', impact.lists_deleted],
    ]),
  }
}

export function reauthenticated(form: SelfDeletionForm): boolean {
  return form.password !== '' || form.passkey !== null
}

/** The delete button works once nothing refuses it, the user re-authenticated and typed the own e-mail address in any case. */
export function canDeleteOwn(impact: SelfDeletionImpact, form: SelfDeletionForm, email: string): boolean {
  return !refused(impact) && reauthenticated(form) && form.typed.trim().toLowerCase() === email.trim().toLowerCase()
}

/** The body of `DELETE /users/me`; a passkey wins over a password typed as well. */
export function deletionBody(impact: SelfDeletionImpact, form: SelfDeletionForm): SelfDeletionRequest {
  return {
    email: form.typed.trim(),
    password: form.passkey ? null : form.password,
    passkey: form.passkey,
    delete_public_recipes: form.deletePublic && offersPublicDeletion(impact),
  }
}
