import { describe, expect, it } from 'vitest'

import { acknowledgementCounts, acknowledgementRows } from '@/features/admin-settings/privacyAcknowledgements'

const person = (id: string, name: string) => ({ id, display_name: name })

const overview = {
  current_version: 3,
  acknowledged: [
    { user: person('1', 'Zora'), version: 3, acknowledged_at: '2026-11-21T10:00:00Z' },
    { user: person('2', 'Anna'), version: 3, acknowledged_at: '2026-11-21T11:00:00Z' },
  ],
  pending: [
    { user: person('3', 'Ben'), version: 2, acknowledged_at: '2026-11-01T10:00:00Z' },
    { user: person('4', 'Alex'), version: null, acknowledged_at: null },
  ],
}

describe('privacyAcknowledgements', () => {
  it('lists the people still asked first, each group by name', () => {
    expect(acknowledgementRows(overview).map((r) => [r.name, r.status])).toEqual([
      ['Alex', 'never'],
      ['Ben', 'outdated'],
      ['Anna', 'current'],
      ['Zora', 'current'],
    ])
  })

  it('counts who accepted the current version', () => {
    expect(acknowledgementCounts(overview)).toEqual({ done: 2, total: 4 })
  })
})
