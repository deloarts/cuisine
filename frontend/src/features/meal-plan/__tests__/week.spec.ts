import { describe, expect, it } from 'vitest'

import { addDays, entriesFor, isoDate, parseIsoDate, startOfWeek, weekDays } from '@/features/meal-plan/week'

describe('week math', () => {
  it('starts weeks on Monday, also from a Sunday', () => {
    expect(startOfWeek('2026-11-21')).toBe('2026-11-16') // Saturday
    expect(startOfWeek('2026-11-22')).toBe('2026-11-16') // Sunday
    expect(startOfWeek('2026-11-16')).toBe('2026-11-16') // Monday
  })

  it('crosses month and year ends', () => {
    expect(addDays('2026-12-30', 3)).toBe('2027-01-02')
    expect(startOfWeek('2027-01-01')).toBe('2026-12-28')
    expect(weekDays('2026-12-28')).toEqual([
      '2026-12-28',
      '2026-12-29',
      '2026-12-30',
      '2026-12-31',
      '2027-01-01',
      '2027-01-02',
      '2027-01-03',
    ])
  })

  it('keeps the calendar date across a daylight saving change', () => {
    expect(addDays('2026-03-28', 1)).toBe('2026-03-29')
    expect(addDays('2026-03-29', 1)).toBe('2026-03-30')
    expect(isoDate(parseIsoDate('2026-10-25'))).toBe('2026-10-25')
  })

  it('picks the entries of one day and slot', () => {
    const entries = [
      { id: 1, plan_date: '2026-11-16', slot: 'dinner' },
      { id: 2, plan_date: '2026-11-16', slot: 'lunch' },
      { id: 3, plan_date: '2026-11-17', slot: 'dinner' },
    ]
    expect(entriesFor(entries, '2026-11-16', 'dinner').map((e) => e.id)).toEqual([1])
  })
})
