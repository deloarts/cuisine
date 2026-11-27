import { describe, expect, it } from 'vitest'

import { formatSeason, monthName, monthRanges, toggleMonth } from '@/shared/cookbook/season'

describe('season months', () => {
  it('toggles a month and keeps the list sorted', () => {
    expect(toggleMonth([5, 3], 4)).toEqual([3, 4, 5])
    expect(toggleMonth([3, 4, 5], 4)).toEqual([3, 5])
    expect(toggleMonth([], 13)).toEqual([])
  })

  it('joins consecutive months and runs over the turn of the year', () => {
    expect(monthRanges([4, 5, 6])).toEqual([[4, 6]])
    expect(monthRanges([1, 2, 11, 12])).toEqual([[11, 2]])
    expect(monthRanges([1, 3, 12])).toEqual([[3, 3], [12, 1]])
    expect(monthRanges([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])).toEqual([[1, 12]])
    expect(monthRanges([])).toEqual([])
  })

  it('formats the ranges with short month names', () => {
    const label = (m: number) => ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m - 1]!
    expect(formatSeason([4, 5, 6, 10], label)).toBe('Apr–Jun, Oct')
    expect(formatSeason([12, 1, 2], label)).toBe('Dec–Feb')
  })
})

describe('month names', () => {
  it("names a month in the reader's language", () => {
    expect(monthName(3, 'en-GB')).toBe('Mar')
    expect(monthName(12, 'en-GB', 'long')).toBe('December')
  })
})
