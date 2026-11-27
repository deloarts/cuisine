import { afterEach, describe, expect, it } from 'vitest'

import { startOfWeek } from '@/shared/cookbook/dates'
import {
  DEFAULT_FORMATS,
  firstWeekday,
  formatDateParts,
  formatTimeParts,
  setDisplayFormats,
} from '@/core/utils/displayFormats'

afterEach(() => setDisplayFormats(DEFAULT_FORMATS))

describe('display formats', () => {
  const date = new Date(2026, 10, 7, 9, 5)

  it('writes every date format', () => {
    expect(formatDateParts(date, 'dd.mm.yyyy')).toBe('07.11.2026')
    expect(formatDateParts(date, 'dd/mm/yyyy')).toBe('07/11/2026')
    expect(formatDateParts(date, 'yyyy-mm-dd')).toBe('2026-11-07')
    expect(formatDateParts(date, 'mm/dd/yyyy')).toBe('11/07/2026')
  })

  it('writes both time formats, noon and midnight included', () => {
    expect(formatTimeParts(date, '24h')).toBe('09:05')
    expect(formatTimeParts(new Date(2026, 0, 1, 0, 30), '12h')).toBe('12:30 am')
    expect(formatTimeParts(new Date(2026, 0, 1, 12, 0), '12h')).toBe('12:00 pm')
  })

  it('starts weeks on the configured day', () => {
    expect(firstWeekday()).toBe(1)
    setDisplayFormats({ first_day_of_week: 'sunday' })
    expect(startOfWeek('2026-11-18')).toBe('2026-11-15')
    setDisplayFormats({ first_day_of_week: 'saturday' })
    expect(startOfWeek('2026-11-18')).toBe('2026-11-14')
  })
})
