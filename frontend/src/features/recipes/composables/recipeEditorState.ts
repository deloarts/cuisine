/**
 * The recipe editor's form state and the rules that turn it into a request.
 * It holds the text of every content locale side by side, so the translation
 * tab edits the same steps and ingredients as the main form, and one save
 * sends everything. Plain functions over a plain object, so the rules are
 * tested without mounting the editor.
 */
import type { RecipeEditResponse, RecipeRequest } from '@/features/recipes/api/recipes'
import {
  MENTION_KINDS,
  parseMentions,
  unlinkMentions,
  type MentionKind,
  type MentionRef,
} from '@/shared/components/richText/mentions'
import { CONTENT_LOCALES } from '@/shared/cookbook/contentLocale'
import type { ContentLocale } from '@/shared/cookbook/types'
import type { WeighableIngredient } from '@/shared/cookbook/units'

export type Difficulty = RecipeRequest['difficulty']

export interface RecipeText {
  title: string
  description: string
  tips: string
}

export type Visibility = NonNullable<RecipeRequest['visibility']>

/** A step line names a catalogue ingredient or another recipe, never both. */
export interface EditorStepIngredient {
  key: string
  /** The line's own id from the backend, sent back so a save keeps it; none for a new line. */
  id?: string | null
  ingredient_id: string | null
  sub_recipe_id: string | null
  ingredient_name: string
  amount: number | null
  unit_id: string | null
  notes: Record<ContentLocale, string>
}

/** An equipment item a step uses, with an optional count and a translatable note. */
export interface EditorStepEquipment {
  key: string
  /** The line's own id from the backend, sent back so a save keeps it; none for a new line. */
  id?: string | null
  equipment_id: string
  equipment_name: string
  count: number | null
  notes: Record<ContentLocale, string>
}

export interface EditorStep {
  key: string
  /** The step's own id from the backend, sent back so a save keeps it; none for a new step. */
  id?: string | null
  text: Record<ContentLocale, string>
  duration_minutes: number | null
  image_id: string | null
  ingredients: EditorStepIngredient[]
  equipment: EditorStepEquipment[]
}

export interface EditorForm {
  original_locale: ContentLocale
  text: Record<ContentLocale, RecipeText>
  base_servings: number
  prep_minutes: number | null
  cook_minutes: number | null
  rest_minutes: number | null
  difficulty: Difficulty
  cover_image_id: string | null
  source_url: string
  source_name: string
  tag_ids: string[]
  yield_amount: number | null
  yield_unit_id: string | null
  visibility: Visibility
  shared_user_ids: string[]
  shared_group_ids: string[]
  // Paired instances the recipe goes to, inside `shared`.
  shared_peer_ids: string[]
  steps: EditorStep[]
  /**
   * The ingredient list declared for the whole recipe, in the shape of a
   * step's lines. The recipe's list takes the larger of it and what the
   * steps use, so it may name what no step uses yet.
   */
  ingredients: EditorStepIngredient[]
}

export type EditorError =
  | 'titleRequired'
  | 'stepsRequired'
  | 'stepTextRequired'
  | 'servingsInvalid'
  | 'ingredientMissing'
  | 'yieldIncomplete'
  | 'mentionMissing'

let keySeed = 0
/** A key for v-for that survives reordering; never sent to the backend. */
export function nextKey(): string {
  keySeed += 1
  return `k${keySeed}`
}

function perLocale<T>(make: () => T): Record<ContentLocale, T> {
  return Object.fromEntries(CONTENT_LOCALES.map((l) => [l, make()])) as Record<ContentLocale, T>
}

const emptyText = (): RecipeText => ({ title: '', description: '', tips: '' })

export function emptyStep(): EditorStep {
  return {
    key: nextKey(),
    text: perLocale(() => ''),
    duration_minutes: null,
    image_id: null,
    ingredients: [],
    equipment: [],
  }
}

export function emptyForm(locale: ContentLocale, visibility: Visibility = 'instance'): EditorForm {
  return {
    original_locale: locale,
    text: perLocale(emptyText),
    base_servings: 4,
    prep_minutes: null,
    cook_minutes: null,
    rest_minutes: null,
    difficulty: 'easy',
    cover_image_id: null,
    source_url: '',
    source_name: '',
    tag_ids: [],
    yield_amount: null,
    yield_unit_id: null,
    visibility,
    shared_user_ids: [],
    shared_group_ids: [],
    shared_peer_ids: [],
    steps: [emptyStep()],
    ingredients: [],
  }
}

// The stored visibility, kept as it is: a public recipe stays public in the
// form even while the instance does not allow public recipes.
const VISIBILITIES: Visibility[] = ['private', 'household', 'shared', 'instance', 'peers', 'public']

function asVisibility(value: string): Visibility {
  return (VISIBILITIES as string[]).includes(value) ? (value as Visibility) : 'instance'
}

function asLocale(value: string): ContentLocale {
  return (CONTENT_LOCALES as string[]).includes(value) ? (value as ContentLocale) : 'en-GB'
}

function lineFromEdit(item: RecipeEditResponse['ingredients'][number]): EditorStepIngredient {
  return {
    key: nextKey(),
    id: item.id,
    ingredient_id: item.ingredient_id,
    sub_recipe_id: item.sub_recipe_id,
    ingredient_name: item.ingredient_name,
    amount: item.amount,
    unit_id: item.unit_id,
    notes: perLocale((): string => ''),
  }
}

function fillNotes(row: EditorStepIngredient | undefined, notes: Record<string, { note: string }>) {
  if (!row) return
  for (const [locale, value] of Object.entries(notes)) {
    if (locale in row.notes) row.notes[locale as ContentLocale] = value.note
  }
}

// Builds the form's shape; fillStepTexts then copies the nested per-locale
// step texts and notes, which need the response's keys.
function formFromEdit(recipe: RecipeEditResponse): EditorForm {
  const text = perLocale(emptyText)
  for (const [locale, value] of Object.entries(recipe.translations)) {
    if (locale in text) text[locale as ContentLocale] = { ...value }
  }
  return {
    original_locale: asLocale(recipe.original_locale),
    text,
    base_servings: recipe.base_servings,
    prep_minutes: recipe.prep_minutes,
    cook_minutes: recipe.cook_minutes,
    rest_minutes: recipe.rest_minutes,
    difficulty: recipe.difficulty as Difficulty,
    cover_image_id: recipe.cover_image_id,
    source_url: recipe.source_url ?? '',
    source_name: recipe.source_name ?? '',
    tag_ids: [...recipe.tag_ids],
    yield_amount: recipe.yield_amount,
    yield_unit_id: recipe.yield_unit_id,
    visibility: asVisibility(recipe.visibility),
    shared_user_ids: [...recipe.shared_user_ids],
    shared_group_ids: [...recipe.shared_group_ids],
    shared_peer_ids: (recipe.shared_peers ?? []).map((p) => p.id),
    steps: recipe.steps.map((step) => ({
      key: nextKey(),
      id: step.id,
      text: perLocale((): string => ''),
      duration_minutes: step.duration_minutes,
      image_id: step.image_id,
      ingredients: step.ingredients.map(lineFromEdit),
      equipment: step.equipment.map((item) => ({
        key: nextKey(),
        id: item.id,
        equipment_id: item.equipment_id,
        equipment_name: item.equipment_name,
        count: item.count,
        notes: perLocale((): string => ''),
      })),
    })),
    // A response of a backend from before the declared list has none.
    ingredients: (recipe.ingredients ?? []).map(lineFromEdit),
  }
}

function fillStepTexts(form: EditorForm, recipe: RecipeEditResponse): EditorForm {
  recipe.steps.forEach((step, i) => {
    const target = form.steps[i]
    if (!target) return
    for (const [locale, value] of Object.entries(step.translations)) {
      if (locale in target.text) target.text[locale as ContentLocale] = value.text
    }
    step.ingredients.forEach((item, j) => fillNotes(target.ingredients[j], item.notes))
    step.equipment.forEach((item, j) => {
      const row = target.equipment[j]
      if (!row) return
      for (const [locale, value] of Object.entries(item.notes)) {
        if (locale in row.notes) row.notes[locale as ContentLocale] = value.note
      }
    })
  })
  const declared = recipe.ingredients ?? []
  declared.forEach((item, j) => fillNotes(form.ingredients[j], item.notes))
  return form
}

export function editorFormFrom(recipe: RecipeEditResponse): EditorForm {
  return fillStepTexts(formFromEdit(recipe), recipe)
}

/** The locales that carry a translation: the original, and every one with a title. */
export function translatedLocales(form: EditorForm): ContentLocale[] {
  return CONTENT_LOCALES.filter(
    (l) => l === form.original_locale || form.text[l].title.trim() !== '',
  )
}

/** How far a locale other than the original is translated. */
export function translationState(
  form: EditorForm,
  locale: ContentLocale,
): 'complete' | 'partial' | 'missing' {
  if (form.text[locale].title.trim() === '') return 'missing'
  const stepsDone = form.steps.every((s) => s.text[locale].trim() !== '')
  return stepsDone ? 'complete' : 'partial'
}

/**
 * The steps whose text, in any language, mentions something that is not
 * one of the step's lines or equipment items; the backend refuses those.
 */
export function stepsWithStrayMentions(form: EditorForm): number[] {
  return form.steps.flatMap((step, index) => {
    const stray = Object.values(step.text).some((text) =>
      parseMentions(text).some((m) => !targetFor(step, m)),
    )
    return stray ? [index] : []
  })
}

/**
 * Where the backend's mention check found a token that names nothing of its
 * step: the step's index, the language of the text, and what it named. The
 * 422 carries these fields next to `detail`; anything else answers null.
 */
export interface MentionProblem {
  stepIndex: number
  locale: ContentLocale | null
  kind: MentionKind | null
  id: string | null
}

export function mentionProblemOf(err: unknown): MentionProblem | null {
  const response = (err as { response?: { status?: number; data?: unknown } } | null)?.response
  if (response?.status !== 422 || !response.data || typeof response.data !== 'object') return null
  const data = response.data as Record<string, unknown>
  if (typeof data.step !== 'number' || data.step < 1) return null
  const locale = typeof data.locale === 'string' ? data.locale : null
  const kind = typeof data.mention_kind === 'string' ? data.mention_kind : null
  return {
    stepIndex: data.step - 1,
    locale: locale && (CONTENT_LOCALES as string[]).includes(locale) ? (locale as ContentLocale) : null,
    kind: kind && (MENTION_KINDS as readonly string[]).includes(kind) ? (kind as MentionKind) : null,
    id: typeof data.mention_id === 'string' ? data.mention_id : null,
  }
}

export function validate(form: EditorForm): EditorError[] {
  const errors: EditorError[] = []
  const original = form.original_locale
  if (form.text[original].title.trim() === '') errors.push('titleRequired')
  if (!Number.isInteger(form.base_servings) || form.base_servings < 1) {
    errors.push('servingsInvalid')
  }
  if (form.steps.length === 0) errors.push('stepsRequired')
  else if (form.steps.some((s) => s.text[original].trim() === '')) errors.push('stepTextRequired')
  const lines = [...form.steps.flatMap((s) => s.ingredients), ...form.ingredients]
  if (lines.some((i) => !i.ingredient_id && !i.sub_recipe_id)) {
    errors.push('ingredientMissing')
  }
  if ((form.yield_amount === null) !== (form.yield_unit_id === null)) errors.push('yieldIncomplete')
  if (stepsWithStrayMentions(form).length) errors.push('mentionMissing')
  return errors
}

const blankToNull = (value: string) => (value.trim() === '' ? null : value.trim())

export function toRequest(form: EditorForm): RecipeRequest {
  const locales = translatedLocales(form)
  const pick = <T>(make: (l: ContentLocale) => T | null): Record<string, T> => {
    const out: Record<string, T> = {}
    for (const l of locales) {
      const value = make(l)
      if (value !== null) out[l] = value
    }
    return out
  }
  const lineRequest = (item: EditorStepIngredient) => ({
    ...(item.id ? { id: item.id } : {}),
    ...(item.sub_recipe_id ? { sub_recipe_id: item.sub_recipe_id } : { ingredient_id: item.ingredient_id }),
    amount: item.amount,
    unit_id: item.unit_id,
    notes: pick((l) => (item.notes[l].trim() ? { note: item.notes[l].trim() } : null)),
  })
  return {
    original_locale: form.original_locale,
    translations: pick((l) => ({
      title: form.text[l].title.trim(),
      description: form.text[l].description.trim(),
      tips: form.text[l].tips.trim(),
    })),
    base_servings: form.base_servings,
    prep_minutes: form.prep_minutes,
    cook_minutes: form.cook_minutes,
    rest_minutes: form.rest_minutes,
    difficulty: form.difficulty,
    cover_image_id: form.cover_image_id,
    source_url: blankToNull(form.source_url),
    source_name: blankToNull(form.source_name),
    tag_ids: [...form.tag_ids],
    yield_amount: form.yield_amount,
    yield_unit_id: form.yield_unit_id,
    visibility: form.visibility,
    shared_user_ids: form.visibility === 'shared' ? [...form.shared_user_ids] : [],
    shared_group_ids: form.visibility === 'shared' ? [...form.shared_group_ids] : [],
    shared_peer_ids: form.visibility === 'shared' ? [...form.shared_peer_ids] : [],
    steps: form.steps.map((step) => ({
      // Existing steps and lines send their ids back, so the save keeps them.
      ...(step.id ? { id: step.id } : {}),
      // A step a translation has not reached yet keeps only the locales
      // that have its text; the reader falls back to the original.
      translations: pick((l) => (step.text[l].trim() ? { text: step.text[l].trim() } : null)),
      duration_minutes: step.duration_minutes,
      image_id: step.image_id,
      ingredients: step.ingredients.map(lineRequest),
      equipment: step.equipment.map((item) => ({
        ...(item.id ? { id: item.id } : {}),
        equipment_id: item.equipment_id,
        count: item.count,
        notes: pick((l) => (item.notes[l].trim() ? { note: item.notes[l].trim() } : null)),
      })),
    })),
    ingredients: form.ingredients.map(lineRequest),
  }
}

export function addStep(form: EditorForm, after?: number): void {
  const index = after === undefined ? form.steps.length : after + 1
  form.steps.splice(index, 0, emptyStep())
}

export function removeStep(form: EditorForm, index: number): void {
  form.steps.splice(index, 1)
}

export function moveStep(form: EditorForm, index: number, direction: -1 | 1): void {
  const target = index + direction
  if (target < 0 || target >= form.steps.length) return
  const [step] = form.steps.splice(index, 1)
  if (step) form.steps.splice(target, 0, step)
}

/** What a step line can point at: a catalogue ingredient or another recipe. */
export interface LineTarget {
  id: string
  name: string
  kind?: 'ingredient' | 'recipe'
  /** The picked catalogue ingredient, so the unit picker knows its weights without a fetch. */
  ingredient?: WeighableIngredient
  /** The amount and unit the new line starts with, such as what the declared list still lacks. */
  amount?: number | null
  unit_id?: string | null
}

export function newStepIngredient(target: LineTarget): EditorStepIngredient {
  const isRecipe = target.kind === 'recipe'
  return {
    key: nextKey(),
    ingredient_id: isRecipe ? null : target.id,
    sub_recipe_id: isRecipe ? target.id : null,
    ingredient_name: target.name,
    amount: target.amount ?? null,
    unit_id: target.unit_id ?? null,
    notes: perLocale(() => ''),
  }
}

/**
 * A stored editor draft in the current form shape: drafts written before the
 * declared ingredient list existed have none.
 */
export function upgradeDraft(stored: EditorForm): EditorForm {
  return { ...stored, ingredients: Array.isArray(stored.ingredients) ? stored.ingredients : [] }
}

export function addIngredient(form: EditorForm, stepIndex: number, ingredient: LineTarget): void {
  form.steps[stepIndex]?.ingredients.push(newStepIngredient(ingredient))
}

export function removeIngredient(form: EditorForm, stepIndex: number, index: number): void {
  const step = form.steps[stepIndex]
  if (step) removeLine(step, index)
}

/** Removes a step line; its mentions turn into plain names in every language. */
export function removeLine(step: EditorStep, index: number): void {
  const [row] = step.ingredients.splice(index, 1)
  const id = row?.sub_recipe_id ?? row?.ingredient_id
  if (!row || !id) return
  const kind = row.sub_recipe_id ? 'recipe' : 'ingredient'
  for (const locale of Object.keys(step.text) as ContentLocale[]) {
    step.text[locale] = unlinkMentions(step.text[locale], kind, id)
  }
}

/** The step's line a mention points at, if it has one. */
export function lineFor(step: EditorStep, ref: MentionRef): EditorStepIngredient | undefined {
  if (ref.kind === 'equipment') return undefined
  return step.ingredients.find((i) =>
    ref.kind === 'recipe' ? i.sub_recipe_id === ref.id : i.ingredient_id === ref.id,
  )
}

/** The step's equipment item a mention points at, if it has one. */
export function equipmentFor(step: EditorStep, ref: MentionRef): EditorStepEquipment | undefined {
  return ref.kind === 'equipment' ? step.equipment.find((e) => e.equipment_id === ref.id) : undefined
}

/** The line or equipment item of the step that a mention points at. */
export function targetFor(
  step: EditorStep,
  ref: MentionRef,
): EditorStepIngredient | EditorStepEquipment | undefined {
  return ref.kind === 'equipment' ? equipmentFor(step, ref) : lineFor(step, ref)
}

/** What a step's equipment picker adds: a catalogue item. */
export interface EquipmentTarget {
  id: string
  name: string
}

export function newStepEquipment(target: EquipmentTarget): EditorStepEquipment {
  return {
    key: nextKey(),
    equipment_id: target.id,
    equipment_name: target.name,
    count: null,
    notes: perLocale(() => ''),
  }
}

/** Adds an equipment item to the step unless it already has it. */
export function addEquipment(step: EditorStep, target: EquipmentTarget): void {
  if (!step.equipment.some((e) => e.equipment_id === target.id)) step.equipment.push(newStepEquipment(target))
}

/** Removes an equipment item; its mentions turn into plain names in every language. */
export function removeEquipment(step: EditorStep, index: number): void {
  const [row] = step.equipment.splice(index, 1)
  if (!row) return
  for (const locale of Object.keys(step.text) as ContentLocale[]) {
    step.text[locale] = unlinkMentions(step.text[locale], 'equipment', row.equipment_id)
  }
}

/**
 * A chip was inserted: the step gets what it names unless it has it, a line
 * with no amount yet for an ingredient or recipe, an item for equipment.
 */
export function ensureLine(step: EditorStep, ref: MentionRef): void {
  if (ref.kind === 'equipment') addEquipment(step, { id: ref.id, name: ref.name })
  else if (!lineFor(step, ref)) step.ingredients.push(newStepIngredient({ id: ref.id, name: ref.name, kind: ref.kind }))
}

/** The step's lines and equipment as mention targets, for the `@` suggestions. */
export function lineMentions(step: EditorStep): MentionRef[] {
  const lines = step.ingredients.flatMap((i): MentionRef[] => {
    const id = i.sub_recipe_id ?? i.ingredient_id
    return id ? [{ kind: i.sub_recipe_id ? 'recipe' : 'ingredient', id, name: i.ingredient_name }] : []
  })
  const equipment = step.equipment.map(
    (e): MentionRef => ({ kind: 'equipment', id: e.equipment_id, name: e.equipment_name }),
  )
  return [...lines, ...equipment]
}
