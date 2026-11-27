import { describe, expect, it } from 'vitest'

import { extendedRows, formatNutrient } from '@/features/recipes/utils/nutrients'

describe('extended nutrients', () => {
  it('formats amounts with fewer decimals as they grow and writes µg', () => {
    expect(formatNutrient(0.345, 'mg', 'en-GB')).toBe('0.35 mg')
    expect(formatNutrient(4.24, 'ug', 'en-GB')).toBe('4.2 µg')
    expect(formatNutrient(120.4, 'mg', 'de-AT')).toBe('120 mg')
    expect(formatNutrient(1.5, 'g', 'de-AT')).toBe('1,5 g')
  })

  it('keeps the backend order, labels each key and passes completeness on', () => {
    const rows = extendedRows(
      [
        { key: 'vitamin_c_mg', unit: 'mg', total: 40, per_serving: 10, complete: true },
        { key: 'iron_mg', unit: 'mg', total: 4, per_serving: 1, complete: false },
      ],
      'en-GB',
      (key) => key.toUpperCase(),
    )
    expect(rows).toEqual([
      { key: 'vitamin_c_mg', label: 'VITAMIN_C_MG', value: '10 mg', complete: true },
      { key: 'iron_mg', label: 'IRON_MG', value: '1 mg', complete: false },
    ])
  })
})
