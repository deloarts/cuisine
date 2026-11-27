/**
 * The rules around the two voluntary consents. Health data (allergies,
 * intolerances, diets) needs its consent before the first restriction is
 * stored, and withdrawing it deletes every restriction. AI agents need theirs
 * before an agent token exists, and withdrawing it revokes every agent token.
 * An agent token is a personal access token that carries `use:mcp`; it lives
 * on the AI agents tab, every other token on the tokens tab.
 */
import type { Consent, ConsentKind, PersonalToken } from '@/features/account/api/account'

export const AGENT_PERMISSION = 'use:mcp'

/** The longest lifetime the AI agents tab offers, matching the instance default cap. */
export const AGENT_TOKEN_DAYS = 30

export function consentOf(consents: Consent[], kind: ConsentKind): Consent {
  return consents.find((c) => c.kind === kind) ?? { kind, granted: false, granted_at: null }
}

export function isAgentToken(token: PersonalToken): boolean {
  return token.permissions.includes(AGENT_PERMISSION)
}

export function agentTokens(tokens: PersonalToken[]): PersonalToken[] {
  return tokens.filter(isAgentToken)
}

export function otherTokens(tokens: PersonalToken[]): PersonalToken[] {
  return tokens.filter((t) => !isAgentToken(t))
}

/** A new agent token needs the consent and the right to create tokens at all. */
export function canCreateAgentToken(consent: Consent, canWriteTokens: boolean): boolean {
  return consent.granted && canWriteTokens
}

export interface WithdrawWarning {
  key: string
  count: number
}

/**
 * What the confirmation says before a consent is withdrawn, given how much
 * depends on it: the restrictions that are deleted or the agent tokens that
 * are revoked. With nothing depending on it, the plain message is enough.
 */
export function withdrawWarning(kind: ConsentKind, dependants: number): WithdrawWarning {
  const base = kind === 'health_data' ? 'consents.health.withdraw' : 'consents.agents.withdraw'
  return { key: dependants > 0 ? `${base}Impact` : `${base}Plain`, count: dependants }
}

/**
 * Whether adding a restriction has to ask for the health-data consent first.
 * The answer is yes until the consent is given, so the first restriction is
 * never stored without it.
 */
export function restrictionNeedsConsent(consent: Consent): boolean {
  return !consent.granted
}
