import { describe, expect, it } from 'vitest'

import {
  cleanMessages,
  keepsForever,
  maintenanceChange,
  maintenanceMessageMissing,
} from '@/features/admin-settings/operationsRules'

const off = { enabled: false, messages: { 'de-AT': 'Wartung', 'en-GB': 'Maintenance' } }

describe('maintenanceChange', () => {
  it('tells switching on and off apart from a new message', () => {
    expect(maintenanceChange(off, { ...off, enabled: true })).toBe('on')
    expect(maintenanceChange({ ...off, enabled: true }, off)).toBe('off')
    expect(maintenanceChange(off, { ...off, messages: { 'de-AT': 'Neu' } })).toBe('message')
  })

  it('sees no change in whitespace alone', () => {
    expect(maintenanceChange(off, { ...off, messages: { 'de-AT': ' Wartung ', 'en-GB': 'Maintenance' } })).toBeNull()
  })
})

describe('maintenance messages', () => {
  it('warns about an active mode without any message', () => {
    expect(maintenanceMessageMissing({ enabled: true, messages: { 'de-AT': ' ' } })).toBe(true)
    expect(maintenanceMessageMissing({ enabled: true, messages: { 'en-GB': 'Back soon' } })).toBe(false)
    expect(maintenanceMessageMissing({ enabled: false, messages: {} })).toBe(false)
  })

  it('stores only the locales with text', () => {
    expect(cleanMessages({ 'de-AT': ' Gleich zurück ', 'en-GB': '' })).toEqual({ 'de-AT': 'Gleich zurück' })
  })
})

describe('keepsForever', () => {
  it('reads 0 days as forever', () => {
    expect(keepsForever(0)).toBe(true)
    expect(keepsForever(30)).toBe(false)
  })
})
