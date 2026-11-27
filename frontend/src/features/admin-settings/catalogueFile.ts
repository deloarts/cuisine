/**
 * The catalogue file import: the preview's differing fields as table rows,
 * keyed the way the import takes them (`<kind>:<source id>:<field>`), the
 * new entries per kind, and choosing which differences to accept, field by
 * field or a whole entry at once. Field names and values are those of the
 * reference data updates, so `referenceUpdates.ts` names and formats them.
 */
import type { CatalogueKind, CataloguePreview } from '@/features/admin-settings/api/catalogueFile'

/** The order the kinds are shown in, as the import writes them. */
export const CATALOGUE_KINDS: CatalogueKind[] = ['category', 'family', 'unit', 'tag', 'ingredient', 'equipment']

export interface DifferenceRow {
  /** The accept key, also the table's row key. */
  id: string
  kind: CatalogueKind
  sourceId: string
  name: string
  field: string
  current: unknown
  incoming: unknown
}

export function acceptKey(kind: string, sourceId: string, field: string): string {
  return `${kind}:${sourceId}:${field}`
}

/** One row per differing field, grouped by entry in the preview's order (entries with allergen or diet marker changes first). */
export function differenceRows(preview: CataloguePreview): DifferenceRow[] {
  return preview.entries.flatMap((entry) =>
    entry.differences.map((d) => ({
      id: acceptKey(entry.kind, entry.source_id, d.field),
      kind: entry.kind,
      sourceId: entry.source_id,
      name: entry.name,
      field: d.field,
      current: d.current,
      incoming: d.incoming,
    })),
  )
}

/** The names of the entries the import creates, per kind, sorted. */
export function newEntries(preview: CataloguePreview): { kind: CatalogueKind; names: string[] }[] {
  return CATALOGUE_KINDS.map((kind) => ({
    kind,
    names: preview.entries
      .filter((e) => e.kind === kind && e.local_id === null)
      .map((e) => e.name)
      .sort((a, b) => a.localeCompare(b)),
  })).filter((group) => group.names.length > 0)
}

/** The accept keys of every differing field of one entry. */
export function entryKeys(rows: DifferenceRow[], kind: string, sourceId: string): string[] {
  return rows.filter((r) => r.kind === kind && r.sourceId === sourceId).map((r) => r.id)
}

/** Accepts all of `keys`, or none of them when all are accepted already. */
export function toggleAll(selected: string[], keys: string[]): string[] {
  const chosen = new Set(selected)
  if (keys.every((k) => chosen.has(k))) {
    keys.forEach((k) => chosen.delete(k))
  } else {
    keys.forEach((k) => chosen.add(k))
  }
  return [...chosen]
}

/** The rows the kind and text filters keep; the text matches the entry's name and the field. */
export function filterRows(
  rows: DifferenceRow[],
  kind: string | null,
  matches: (...texts: string[]) => boolean,
): DifferenceRow[] {
  return rows.filter((r) => (!kind || r.kind === kind) && matches(r.name, r.field))
}

/** `cuisine-catalogue-<YYYY-MM-DD>.json`, the name the backend gives the file too. */
export function catalogueFileName(day: Date): string {
  return `cuisine-catalogue-${day.toISOString().slice(0, 10)}.json`
}
