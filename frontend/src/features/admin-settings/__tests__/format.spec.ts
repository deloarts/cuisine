import { describe, expect, it } from 'vitest'

import { formatBytes, formatUptime } from '@/features/admin-settings/format'
import { visibleTabs } from '@/features/admin-settings/adminTabs'

describe('formatBytes', () => {
  it('picks a unit and rounds', () => {
    expect(formatBytes(512, 'en-GB')).toBe('512 B')
    expect(formatBytes(1536, 'en-GB')).toBe('1.5 KB')
    expect(formatBytes(5 * 1024 ** 3, 'de-AT')).toBe('5 GB')
    expect(formatBytes(null, 'en-GB')).toBe('–')
  })
})

describe('formatUptime', () => {
  const now = new Date('2026-11-21T12:00:00Z')
  it('shows the two largest parts', () => {
    expect(formatUptime('2026-11-21T11:53:00Z', now)).toBe('7 min')
    expect(formatUptime('2026-11-21T06:48:00Z', now)).toBe('5 h 12 min')
    expect(formatUptime('2026-11-18T08:00:00Z', now)).toBe('3 d 4 h')
  })
})

describe('visibleTabs', () => {
  it('shows a tab when one of its sections is allowed and keeps only those sections', () => {
    const tabs = visibleTabs((p) => p === 'read:security_log')
    expect(tabs.map((t) => t.value)).toEqual(['auth', 'agents', 'operations'])
    expect(tabs[0]?.sections.map((s) => s.key)).toEqual(['securityLog'])
    expect(tabs[2]?.sections.map((s) => s.key)).toEqual(['logs'])
  })

  it('hides the tab of a switched-off feature', () => {
    const settings = (p: string) => p === 'read:settings'
    expect(visibleTabs(settings, () => false).map((t) => t.value)).not.toContain('peers')
    expect(visibleTabs(settings, (f) => f === 'peering').map((t) => t.value)).toContain('peers')
  })

  it('shows nothing without an admin permission', () => {
    expect(visibleTabs(() => false)).toEqual([])
  })
})
