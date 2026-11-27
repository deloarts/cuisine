/**
 * The variation editor's form and its conversion to and from the API. A
 * variation is a name, a note, a private flag and a list of changes; each
 * change names a step of the recipe as it is now by its number from 1
 * (`extra_step` counts "after step n", 0 for the start, and a `swap`
 * without a step applies to the whole recipe). Existing changes keep their
 * id, since adopting picks changes by id.
 */
import type {
  VariationChangeKind,
  VariationChangeRequest,
  VariationChangeView,
  VariationRequest,
  VariationResponse,
} from '@/features/recipes/api/recipes'
import { nextKey } from '@/features/recipes/composables/recipeEditorState'
import { unlinkMentions } from '@/shared/components/richText/mentions'
import type { ContentLocale } from '@/shared/cookbook/types'

export const CHANGE_KINDS: readonly VariationChangeKind[] = [
  'swap',
  'add_line',
  'remove_line',
  'step_text',
  'extra_step',
]

/** At most this many changes per variation, as the backend allows. */
export const MAX_CHANGES = 100

export interface VariationLineDraft {
  key: string
  ingredient_id: string
  name: string
  amount: number | null
  unit_id: string | null
  note: string
}

export interface VariationEquipmentDraft {
  key: string
  equipment_id: string
  name: string
  count: number | null
  note: string
}

export interface ChangeDraft {
  key: string
  id: string | null
  kind: VariationChangeKind
  step: number | null
  /** The line a swap or a removal names, or the ingredient an added line uses. */
  ingredient_id: string | null
  sub_recipe_id: string | null
  /** The name of that line, shown in the editor only. */
  target_name: string
  to_ingredient_id: string | null
  to_name: string
  keep_amount: boolean
  amount: number | null
  unit_id: string | null
  note: string
  text: string
  duration_minutes: number | null
  lines: VariationLineDraft[]
  equipment: VariationEquipmentDraft[]
}

export interface VariationForm {
  name: string
  note: string
  locale: ContentLocale
  private: boolean
  changes: ChangeDraft[]
}

export type VariationError = 'nameRequired' | 'changesRequired' | 'changeIncomplete' | 'tooManyChanges'

export function emptyVariationForm(locale: ContentLocale): VariationForm {
  return { name: '', note: '', locale, private: false, changes: [] }
}

/** A new change of a kind; a swap starts on the whole recipe, the rest on the given step. */
export function newChange(kind: VariationChangeKind, step: number | null = null): ChangeDraft {
  return {
    key: nextKey(),
    id: null,
    kind,
    step: kind === 'swap' ? step : (step ?? (kind === 'extra_step' ? 0 : 1)),
    ingredient_id: null,
    sub_recipe_id: null,
    target_name: '',
    to_ingredient_id: null,
    to_name: '',
    keep_amount: true,
    amount: null,
    unit_id: null,
    note: '',
    text: '',
    duration_minutes: null,
    lines: [],
    equipment: [],
  }
}

function draftFrom(change: VariationChangeView): ChangeDraft {
  return {
    key: nextKey(),
    id: change.id,
    kind: change.kind as VariationChangeKind,
    step: change.step,
    ingredient_id: change.ingredient_id,
    sub_recipe_id: change.sub_recipe?.id ?? null,
    target_name: change.ingredient_name ?? change.sub_recipe?.title ?? '',
    to_ingredient_id: change.to_ingredient_id,
    to_name: change.to_ingredient_name ?? '',
    keep_amount: change.keep_amount,
    amount: change.amount,
    unit_id: change.unit?.id ?? null,
    note: change.note,
    text: change.text,
    duration_minutes: change.duration_minutes,
    lines: change.lines.flatMap((line) =>
      line.ingredient_id
        ? [
            {
              key: nextKey(),
              ingredient_id: line.ingredient_id,
              name: line.ingredient_name,
              amount: line.amount,
              unit_id: line.unit?.id ?? null,
              note: line.note,
            },
          ]
        : [],
    ),
    equipment: change.equipment.flatMap((item) =>
      item.equipment
        ? [
            {
              key: nextKey(),
              equipment_id: item.equipment.id,
              name: item.equipment.name,
              count: item.count,
              note: item.note,
            },
          ]
        : [],
    ),
  }
}

/**
 * The form of an existing variation. A change whose ingredient no longer
 * exists cannot be sent back, so it is left out and saving drops it.
 */
export function variationFormFrom(variation: VariationResponse): VariationForm {
  return {
    name: variation.name,
    note: variation.note,
    locale: variation.locale as ContentLocale,
    private: variation.private,
    changes: variation.changes.filter((c) => c.available).map(draftFrom),
  }
}

/** Whether a change has everything its kind needs. */
export function changeComplete(change: ChangeDraft): boolean {
  const hasTarget = change.ingredient_id !== null || change.sub_recipe_id !== null
  switch (change.kind) {
    case 'swap':
      return change.ingredient_id !== null && change.to_ingredient_id !== null
    case 'add_line':
      return (change.step ?? 0) >= 1 && hasTarget
    case 'remove_line':
      return (change.step ?? 0) >= 1 && hasTarget
    case 'step_text':
      return (change.step ?? 0) >= 1 && change.text.trim() !== ''
    case 'extra_step':
      return (change.step ?? -1) >= 0 && change.text.trim() !== ''
  }
}

/** The indexes of the changes that still miss something. */
export function incompleteChanges(form: VariationForm): number[] {
  return form.changes.flatMap((c, i) => (changeComplete(c) ? [] : [i]))
}

export function validateVariation(form: VariationForm): VariationError[] {
  const errors: VariationError[] = []
  if (!form.name.trim()) errors.push('nameRequired')
  if (!form.changes.length) errors.push('changesRequired')
  if (form.changes.length > MAX_CHANGES) errors.push('tooManyChanges')
  if (incompleteChanges(form).length) errors.push('changeIncomplete')
  return errors
}

function changeRequest(change: ChangeDraft): VariationChangeRequest {
  const base: VariationChangeRequest = {
    kind: change.kind,
    id: change.id,
    step: change.step,
    keep_amount: true,
    note: '',
    text: '',
  }
  switch (change.kind) {
    case 'swap':
      return {
        ...base,
        ingredient_id: change.ingredient_id,
        to_ingredient_id: change.to_ingredient_id,
        keep_amount: change.keep_amount,
        amount: change.keep_amount ? null : change.amount,
        unit_id: change.keep_amount ? null : change.unit_id,
        note: change.keep_amount ? '' : change.note.trim(),
      }
    case 'add_line':
      return {
        ...base,
        ingredient_id: change.ingredient_id,
        sub_recipe_id: change.sub_recipe_id,
        amount: change.amount,
        unit_id: change.amount === null ? null : change.unit_id,
        note: change.note.trim(),
      }
    case 'remove_line':
      return { ...base, ingredient_id: change.ingredient_id, sub_recipe_id: change.sub_recipe_id }
    case 'step_text':
      return { ...base, text: change.text.trim() }
    case 'extra_step':
      return {
        ...base,
        text: change.text.trim(),
        duration_minutes: change.duration_minutes,
        lines: change.lines.map((line) => ({
          ingredient_id: line.ingredient_id,
          amount: line.amount,
          unit_id: line.amount === null ? null : line.unit_id,
          note: line.note.trim(),
        })),
        equipment: change.equipment.map((item) => ({
          equipment_id: item.equipment_id,
          count: item.count,
          note: item.note.trim(),
        })),
      }
  }
}

export function toVariationRequest(form: VariationForm): VariationRequest {
  return {
    name: form.name.trim(),
    note: form.note.trim(),
    locale: form.locale,
    private: form.private,
    changes: form.changes.map(changeRequest),
  }
}

/** Picking another kind keeps the step where it makes sense and clears the rest. */
export function changeKind(change: ChangeDraft, kind: VariationChangeKind): ChangeDraft {
  const fresh = newChange(kind, kind === 'swap' ? change.step : change.step ?? undefined)
  if (kind !== 'swap' && fresh.step === null) fresh.step = kind === 'extra_step' ? 0 : 1
  return { ...fresh, key: change.key, id: change.id }
}

/** Points a swap or a removal at a line, or an added line at an ingredient or a recipe. */
export function setTarget(change: ChangeDraft, target: { kind: 'ingredient' | 'recipe'; id: string; name: string }) {
  change.ingredient_id = target.kind === 'ingredient' ? target.id : null
  change.sub_recipe_id = target.kind === 'recipe' ? target.id : null
  change.target_name = target.name
}

export function addExtraLine(change: ChangeDraft, ingredient: { id: string; name: string }) {
  if (change.lines.some((l) => l.ingredient_id === ingredient.id)) return
  change.lines.push({
    key: nextKey(),
    ingredient_id: ingredient.id,
    name: ingredient.name,
    amount: null,
    unit_id: null,
    note: '',
  })
}

export function addExtraEquipment(change: ChangeDraft, item: { id: string; name: string }) {
  if (change.equipment.some((e) => e.equipment_id === item.id)) return
  change.equipment.push({ key: nextKey(), equipment_id: item.id, name: item.name, count: null, note: '' })
}

/** Removing a line of an extra step turns its chips in the step text into plain names. */
export function removeExtraLine(change: ChangeDraft, index: number) {
  const [line] = change.lines.splice(index, 1)
  if (line) change.text = unlinkMentions(change.text, 'ingredient', line.ingredient_id)
}

export function removeExtraEquipment(change: ChangeDraft, index: number) {
  const [item] = change.equipment.splice(index, 1)
  if (item) change.text = unlinkMentions(change.text, 'equipment', item.equipment_id)
}
