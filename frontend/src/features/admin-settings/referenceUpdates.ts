/**
 * The reference data updates view: the seed fields an admin (or anyone with
 * the catalogue rights) changed, where the shipped seed now has another
 * value. The backend lists allergens and diet markers first, because a stale
 * allergen is the one difference that can hurt someone; this module names
 * the fields and turns the stored values into readable text.
 */
import type { Schemas } from '@/core/api/generated'

export type ReferenceUpdate = Schemas['ReferenceUpdateResponse']

/** Fields that drive the allergy and diet warnings. */
export const SAFETY_FIELDS = ['allergens', 'diet_markers']

export const REFERENCE_KINDS = ['ingredient', 'family', 'category', 'unit', 'tag', 'equipment']

export const KNOWN_FIELDS = [
  'names',
  'aliases',
  'category',
  'family',
  'nutrition',
  'extended',
  'density_g_per_ml',
  'conversions',
  'allergens',
  'diet_markers',
  'season_months',
  'to_base',
  'kind',
  'color',
  'icon',
  'basic',
]

export interface FieldName {
  /** The field family, e.g. `names` for `names.de-AT`, or the whole id when unknown. */
  base: string
  /** The part after the dot (a locale or a nutrient), or null. */
  detail: string | null
  known: boolean
}

export function fieldName(field: string): FieldName {
  const dot = field.indexOf('.')
  const base = dot === -1 ? field : field.slice(0, dot)
  const detail = dot === -1 ? null : field.slice(dot + 1)
  return { base, detail, known: KNOWN_FIELDS.includes(base) }
}

export function isSafetyField(field: string): boolean {
  return SAFETY_FIELDS.includes(fieldName(field).base)
}

/** Stable key for one row, for the table and for removing an accepted row. */
export function rowKey(row: Pick<ReferenceUpdate, 'kind' | 'key' | 'field'>): string {
  return `${row.kind}:${row.key}:${row.field}`
}

export interface ValueLabels {
  /** Translates an allergen or diet marker key. */
  marker: (field: 'allergens' | 'diet_markers', key: string) => string
  month: (month: number) => string
  yes: string
  no: string
  empty: string
}

/**
 * A stored value as text: lists joined, allergens and diet markers and
 * months translated, conversions as `unit: grams`, unit names as
 * `name / plural / abbreviation`, an absent value as the empty marker.
 */
export function formatValue(field: string, value: unknown, labels: ValueLabels): string {
  const { base } = fieldName(field)
  if (value === null || value === undefined || value === '') return labels.empty
  if (typeof value === 'boolean') return value ? labels.yes : labels.no
  if (Array.isArray(value)) {
    if (value.length === 0) return labels.empty
    if (base === 'allergens' || base === 'diet_markers') {
      return value.map((v) => labels.marker(base, String(v))).join(', ')
    }
    if (base === 'season_months') return value.map((v) => labels.month(Number(v))).join(', ')
    if (base === 'names') return value.map((v) => (v === null || v === '' ? labels.empty : String(v))).join(' / ')
    return value.map(String).join(', ')
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length === 0) return labels.empty
    return entries.map(([k, v]) => `${k}: ${String(v)}`).join(', ')
  }
  return String(value)
}

/** The rows the kind and text filters keep; the text matches name, key and field. */
export function filterUpdates(
  rows: ReferenceUpdate[],
  kind: string | null,
  matches: (...texts: string[]) => boolean,
): ReferenceUpdate[] {
  return rows.filter((r) => (!kind || r.kind === kind) && matches(r.name, r.key, r.field))
}
