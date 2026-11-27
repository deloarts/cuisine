import { describe, expect, it } from 'vitest'

import { formatAmount } from '@/features/recipes/utils/scaling'

describe('formatAmount for small metric amounts', () => {
  it('stays exact by default', () => {
    expect(formatAmount(0.125, 'de-AT', 'volume', { unitCode: 'l' })).toBe('0,125')
    expect(formatAmount(0.25, 'de-AT', 'mass', { unitCode: 'kg' })).toBe('0,25')
    expect(formatAmount(1.25, 'de-AT', 'volume', { unitCode: 'l' })).toBe('1,25')
    expect(formatAmount(1.5, 'de-AT', 'volume', { unitCode: 'tbsp' })).toBe('1,5')
  })

  it('reads kitchen fractions of a litre or kilogram when the user wants them', () => {
    const fractions = { style: 'fractions' as const }
    expect(formatAmount(0.125, 'de-AT', 'volume', { ...fractions, unitCode: 'l' })).toBe('⅛')
    expect(formatAmount(1.5, 'de-AT', 'mass', { ...fractions, unitCode: 'kg' })).toBe('1 ½')
    // Thirds and millilitres stay decimal.
    expect(formatAmount(1 / 3, 'de-AT', 'volume', { ...fractions, unitCode: 'l' })).toBe('0,333')
    expect(formatAmount(0.5, 'de-AT', 'volume', { ...fractions, unitCode: 'ml' })).toBe('0,5')
  })
})
