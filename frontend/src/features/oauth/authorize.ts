/**
 * The rules of the consent page that need no component: reading the
 * authorization request from the URL, which permissions start ticked, and
 * which one cannot be unticked.
 */
import type { LocationQuery } from 'vue-router'

import type { AuthorizationPrompt, AuthorizationRequest } from '@/features/oauth/api/oauth'

/** Every connection can read the cookbook, so this permission is always granted. */
export const BASE_PERMISSION = 'use:mcp'

const OPTIONAL_FIELDS = [
  'redirect_uri',
  'response_type',
  'code_challenge',
  'code_challenge_method',
  'state',
  'scope',
  'resource',
] as const

function first(value: LocationQuery[string] | undefined): string | null {
  const item = Array.isArray(value) ? value[0] : value
  return typeof item === 'string' && item !== '' ? item : null
}

/**
 * The authorization request in the URL, or null when it names no client,
 * which no app would send. Parameters the backend does not know are left out,
 * since its schema refuses unknown fields.
 */
export function authorizationRequest(query: LocationQuery): AuthorizationRequest | null {
  const clientId = first(query.client_id)
  if (!clientId) return null
  const request: AuthorizationRequest = { client_id: clientId }
  for (const field of OPTIONAL_FIELDS) {
    const value = first(query[field])
    if (value !== null) request[field] = value
  }
  return request
}

/** The permissions ticked when the page opens: what the app asked for. */
export function initialChoice(prompt: AuthorizationPrompt): string[] {
  const asked = prompt.requested.filter((p) => prompt.offered.includes(p))
  return asked.includes(BASE_PERMISSION) ? asked : [BASE_PERMISSION, ...asked]
}

export function isFixed(permission: string): boolean {
  return permission === BASE_PERMISSION
}
