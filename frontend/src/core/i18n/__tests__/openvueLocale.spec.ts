import { describe, expect, it } from 'vitest'

import { applyOpenVueLocale } from '@/core/i18n/openvueLocale'

describe('applyOpenVueLocale', () => {
  it('switches the texts and keeps the date settings', () => {
    const config: { locale?: Record<string, unknown> } = {
      locale: { dateFormat: 'yy-mm-dd', firstDayOfWeek: 1, aria: { zoomImage: 'Zoom Image' } },
    }
    applyOpenVueLocale(config, 'deAT')
    expect(config.locale?.emptySearchMessage).toBe('Nichts gefunden')
    expect(config.locale?.dateFormat).toBe('yy-mm-dd')
    const aria = config.locale?.aria as Record<string, string>
    expect(aria.close).toBe('Schließen')
    expect(aria.zoomImage).toBe('Zoom Image')
    applyOpenVueLocale(config, 'enGB')
    expect(config.locale?.emptySearchMessage).toBe('No results found')
  })
})
