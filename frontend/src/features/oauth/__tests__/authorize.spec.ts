import { describe, expect, it } from 'vitest'

import type { AuthorizationPrompt } from '@/features/oauth/api/oauth'
import { authorizationRequest, initialChoice, isFixed } from '@/features/oauth/authorize'

function prompt(requested: string[], offered = ['use:mcp', 'write:recipes', 'write:ingredients']): AuthorizationPrompt {
  return {
    client_name: 'ChatGPT',
    client_uri: null,
    redirect_host: 'chatgpt.com',
    offered,
    requested,
    error_redirect: null,
  }
}

describe('authorizationRequest', () => {
  it('reads the known parameters and drops the rest', () => {
    expect(
      authorizationRequest({
        client_id: 'cuisine_oc_1',
        response_type: 'code',
        code_challenge: 'abc',
        code_challenge_method: 'S256',
        state: ['first', 'second'],
        scope: '',
        prompt: 'consent',
      }),
    ).toEqual({
      client_id: 'cuisine_oc_1',
      response_type: 'code',
      code_challenge: 'abc',
      code_challenge_method: 'S256',
      state: 'first',
    })
  })

  it('needs a client', () => {
    expect(authorizationRequest({ response_type: 'code' })).toBeNull()
    expect(authorizationRequest({ client_id: '' })).toBeNull()
  })
})

describe('initialChoice', () => {
  it('ticks what the app asked for, always with reading', () => {
    expect(initialChoice(prompt(['write:recipes']))).toEqual(['use:mcp', 'write:recipes'])
    expect(initialChoice(prompt(['use:mcp', 'write:ingredients']))).toEqual(['use:mcp', 'write:ingredients'])
  })

  it('never ticks a permission the person cannot grant', () => {
    expect(initialChoice(prompt(['use:mcp', 'write:recipes'], ['use:mcp']))).toEqual(['use:mcp'])
  })

  it('keeps reading fixed', () => {
    expect(isFixed('use:mcp')).toBe(true)
    expect(isFixed('write:recipes')).toBe(false)
  })
})
