import { describe, expect, it } from 'vitest'

import { byDate, initials, monthGrid, monthRange, shiftMonth, weekdayNames } from '@/features/cooked/month'

describe('month math', () => {
  it('covers a month with whole Monday-first weeks', () => {
    const grid = monthGrid('2026-11')
    expect(grid[0]?.[0]).toEqual({ date: '2026-10-26', inMonth: false })
    expect(grid.at(-1)?.at(-1)).toEqual({ date: '2026-12-06', inMonth: false })
    expect(grid).toHaveLength(6)
    expect(grid.flat().filter((c) => c.inMonth)).toHaveLength(30)
  })

  it('handles a month that starts on Monday and February in a leap year', () => {
    expect(monthGrid('2027-02')[0]?.[0]?.date).toBe('2027-02-01')
    expect(monthRange('2028-02')).toEqual({ from: '2028-02-01', to: '2028-02-29' })
  })

  it('shifts across years', () => {
    expect(shiftMonth('2026-12', 1)).toBe('2027-01')
    expect(shiftMonth('2026-01', -1)).toBe('2025-12')
    expect(shiftMonth('2026-11', -12)).toBe('2025-11')
  })

  it('groups events by date and builds initials', () => {
    const map = byDate([
      { id: 1, cooked_on: '2026-11-02' },
      { id: 2, cooked_on: '2026-11-02' },
      { id: 3, cooked_on: '2026-11-03' },
    ])
    expect(map.get('2026-11-02')?.map((e) => e.id)).toEqual([1, 2])
    expect(initials('Anna Maria Huber')).toBe('AM')
    expect(initials('admin')).toBe('A')
  })

  it('names the weekdays from Monday', () => {
    expect(weekdayNames('en-GB')[0]).toBe('Mon')
  })
})
