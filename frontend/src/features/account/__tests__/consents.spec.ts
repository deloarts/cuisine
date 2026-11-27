import { describe, expect, it } from 'vitest'

import type { Consent, PersonalToken } from '@/features/account/api/account'
import {
  agentTokens,
  canCreateAgentToken,
  consentOf,
  otherTokens,
  restrictionNeedsConsent,
  withdrawWarning,
} from '@/features/account/consents'

const token = (id: string, permissions: string[]) => ({ id, permissions }) as PersonalToken
const granted: Consent = { kind: 'ai_agents', granted: true, granted_at: '2026-11-21T10:00:00Z' }

describe('consents', () => {
  it('treats a consent the list lacks as not given', () => {
    expect(consentOf([granted], 'ai_agents').granted).toBe(true)
    expect(consentOf([granted], 'health_data')).toEqual({ kind: 'health_data', granted: false, granted_at: null })
  })

  it('puts tokens with use:mcp on the agents tab and the rest on the tokens tab', () => {
    const tokens = [token('a', ['use:mcp', 'read:recipes']), token('b', ['read:recipes'])]
    expect(agentTokens(tokens).map((t) => t.id)).toEqual(['a'])
    expect(otherTokens(tokens).map((t) => t.id)).toEqual(['b'])
  })

  it('creates agent tokens only with the consent and the token permission', () => {
    expect(canCreateAgentToken(granted, true)).toBe(true)
    expect(canCreateAgentToken(granted, false)).toBe(false)
    expect(canCreateAgentToken({ ...granted, granted: false }, true)).toBe(false)
  })

  it('asks for the health-data consent before the first restriction', () => {
    expect(restrictionNeedsConsent({ kind: 'health_data', granted: false, granted_at: null })).toBe(true)
    expect(restrictionNeedsConsent({ kind: 'health_data', granted: true, granted_at: 'x' })).toBe(false)
  })

  it('warns about what withdrawing deletes or revokes', () => {
    expect(withdrawWarning('health_data', 3)).toEqual({ key: 'consents.health.withdrawImpact', count: 3 })
    expect(withdrawWarning('health_data', 0)).toEqual({ key: 'consents.health.withdrawPlain', count: 0 })
    expect(withdrawWarning('ai_agents', 1).key).toBe('consents.agents.withdrawImpact')
  })
})
