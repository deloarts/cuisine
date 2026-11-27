import { describe, expect, it } from 'vitest'

import { activeCount, emptyValues, parseQuery, toQuery } from '@/shared/composables/urlFilters'

const spec = { q: 'string', mine: 'boolean', min: 'number', tags: 'list' } as const

describe('url filters', () => {
  it('reads values of every kind and ignores junk', () => {
    expect(parseQuery(spec, { q: 'egg', mine: '1', min: '120', tags: 'a,b' })).toEqual({
      q: 'egg',
      mine: true,
      min: 120,
      tags: ['a', 'b'],
    })
    expect(parseQuery(spec, { min: 'abc', mine: '0', q: '' })).toEqual(emptyValues(spec))
  })

  it('writes only active filters and round-trips', () => {
    const values = { q: 'egg', mine: false, min: 0, tags: [] as string[] }
    expect(toQuery(spec, values)).toEqual({ q: 'egg', min: '0' })
    expect(parseQuery(spec, toQuery(spec, values) as never)).toEqual(values)
    expect(activeCount(spec, values)).toBe(2)
    expect(activeCount(spec, emptyValues(spec))).toBe(0)
  })
})
