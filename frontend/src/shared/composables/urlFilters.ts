/**
 * Filter state that lives in the URL's query string, so a filtered list can
 * be bookmarked, shared and restored with the back button. A spec names
 * each filter and its kind; empty values never appear in the URL.
 */
import type { LocationQuery, LocationQueryRaw } from 'vue-router'

export type UrlFilterKind = 'string' | 'boolean' | 'number' | 'list'
export type UrlFilterSpec = Record<string, UrlFilterKind>

type ValueOf<K extends UrlFilterKind> = K extends 'string'
  ? string | null
  : K extends 'boolean'
    ? boolean
    : K extends 'number'
      ? number | null
      : string[]

export type UrlFilterValues<S extends UrlFilterSpec> = { -readonly [K in keyof S]: ValueOf<S[K]> }

function first(value: LocationQuery[string] | undefined): string | null {
  const raw = Array.isArray(value) ? value[0] : value
  return raw === null || raw === undefined || raw === '' ? null : raw
}

export function emptyValues<S extends UrlFilterSpec>(spec: S): UrlFilterValues<S> {
  const values: Record<string, unknown> = {}
  for (const [key, kind] of Object.entries(spec)) {
    values[key] = kind === 'boolean' ? false : kind === 'list' ? [] : null
  }
  return values as UrlFilterValues<S>
}

export function parseQuery<S extends UrlFilterSpec>(spec: S, query: LocationQuery): UrlFilterValues<S> {
  const values = emptyValues(spec) as Record<string, unknown>
  for (const [key, kind] of Object.entries(spec)) {
    const raw = first(query[key])
    if (raw === null) continue
    if (kind === 'string') values[key] = raw
    else if (kind === 'boolean') values[key] = raw === '1' || raw === 'true'
    else if (kind === 'number') {
      const n = Number(raw)
      values[key] = Number.isFinite(n) ? n : null
    } else values[key] = raw.split(',').filter(Boolean)
  }
  return values as UrlFilterValues<S>
}

/** The filters as query entries; inactive filters are left out. */
export function toQuery<S extends UrlFilterSpec>(spec: S, values: UrlFilterValues<S>): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  for (const [key, kind] of Object.entries(spec)) {
    const value = (values as Record<string, unknown>)[key]
    if (kind === 'boolean') {
      if (value) query[key] = '1'
    } else if (kind === 'list') {
      if (Array.isArray(value) && value.length) query[key] = value.join(',')
    } else if (value !== null && value !== undefined && value !== '') {
      query[key] = String(value)
    }
  }
  return query
}

/** How many filters are set, for the "clear filters" action. */
export function activeCount<S extends UrlFilterSpec>(spec: S, values: UrlFilterValues<S>): number {
  return Object.keys(toQuery(spec, values)).length
}
