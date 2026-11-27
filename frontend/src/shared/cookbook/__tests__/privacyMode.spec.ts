import { describe, expect, it } from 'vitest'

import {
  effectiveDefault,
  effectiveVisibility,
  isVisibility,
  modeOfSnapshot,
  offeredVisibilities,
  privacyMode,
} from '@/shared/cookbook/privacyMode'

const closed = { allow_public_recipes: false } as const

describe('privacyMode', () => {
  it('names the locked modes and the free choice', () => {
    expect(privacyMode({ default_recipe_visibility: 'instance', users_may_change_visibility: false, ...closed })).toBe('instance')
    expect(privacyMode({ default_recipe_visibility: 'private', users_may_change_visibility: false, ...closed })).toBe('private')
    expect(privacyMode({ default_recipe_visibility: 'private', users_may_change_visibility: true, ...closed })).toBe('choice')
  })

  it('calls any other locked default fixed', () => {
    expect(privacyMode({ default_recipe_visibility: 'household', users_may_change_visibility: false, ...closed })).toBe('fixed')
  })

  it('names the public mode only while public recipes are allowed', () => {
    const locked = { default_recipe_visibility: 'public', users_may_change_visibility: false } as const
    expect(privacyMode({ ...locked, allow_public_recipes: true })).toBe('public')
    expect(privacyMode({ ...locked, allow_public_recipes: false })).toBe('instance')
  })
})

describe('effectiveDefault', () => {
  const open = { default_recipe_visibility: 'instance', users_may_change_visibility: true, ...closed } as const
  const locked = { default_recipe_visibility: 'private', users_may_change_visibility: false, ...closed } as const

  it('uses the own default only while users may choose', () => {
    expect(effectiveDefault(open, 'household')).toBe('household')
    expect(effectiveDefault(locked, 'instance')).toBe('private')
  })

  it('falls back to the instance default without a valid own one', () => {
    expect(effectiveDefault(open, null)).toBe('instance')
    expect(effectiveDefault(open, 'nonsense')).toBe('instance')
    expect(isVisibility('shared')).toBe(true)
  })

  it('reads an own public default as instance while public recipes are not allowed', () => {
    expect(effectiveDefault(open, 'public')).toBe('instance')
    expect(effectiveDefault({ ...open, allow_public_recipes: true }, 'public')).toBe('public')
  })
})

describe('public recipes switch', () => {
  it('offers public only while allowed, in ladder order', () => {
    expect(offeredVisibilities(false)).toEqual(['private', 'household', 'shared', 'instance'])
    expect(offeredVisibilities(true)).toEqual(['private', 'household', 'shared', 'instance', 'public'])
  })

  it('reads a stored public as instance while off', () => {
    expect(effectiveVisibility('public', false)).toBe('instance')
    expect(effectiveVisibility('public', true)).toBe('public')
    expect(effectiveVisibility('shared', false)).toBe('shared')
  })
})

describe('modeOfSnapshot', () => {
  it('maps the snapshot of the current user onto the same modes', () => {
    expect(modeOfSnapshot({ mode: 'instance', default_visibility: 'instance', allow_public_recipes: false })).toBe('instance')
    expect(modeOfSnapshot({ mode: 'public', default_visibility: 'public', allow_public_recipes: true })).toBe('public')
    expect(modeOfSnapshot({ mode: 'user_choice', default_visibility: 'household', allow_public_recipes: false })).toBe('choice')
    expect(modeOfSnapshot({ mode: 'private', default_visibility: 'private', allow_public_recipes: false })).toBe('private')
    expect(modeOfSnapshot({ mode: 'private', default_visibility: 'household', allow_public_recipes: false })).toBe('fixed')
  })
})

describe('peering switch', () => {
  it('offers paired instances only while peering is on, between instance and public', () => {
    expect(offeredVisibilities(true, false)).not.toContain('peers')
    expect(offeredVisibilities(true, true)).toEqual([
      'private',
      'household',
      'shared',
      'instance',
      'peers',
      'public',
    ])
  })

  it('reads a stored peers as instance while peering is off', () => {
    expect(effectiveVisibility('peers', false)).toBe('instance')
    expect(effectiveVisibility('peers', false, true)).toBe('peers')
  })

  it('names the peers mode only while peering is on', () => {
    const locked = { default_recipe_visibility: 'peers', users_may_change_visibility: false, ...closed } as const
    expect(privacyMode(locked, true)).toBe('peers')
    expect(privacyMode(locked)).toBe('instance')
    expect(modeOfSnapshot({ mode: 'peers', default_visibility: 'peers', allow_public_recipes: false })).toBe('peers')
  })

  it('reads an own peers default as instance while peering is off', () => {
    const open = { default_recipe_visibility: 'instance', users_may_change_visibility: true, ...closed } as const
    expect(effectiveDefault(open, 'peers')).toBe('instance')
    expect(effectiveDefault(open, 'peers', true)).toBe('peers')
  })
})
