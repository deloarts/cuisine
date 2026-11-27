import { flushPromises, mount } from '@vue/test-utils'
import { AxiosError, AxiosHeaders } from 'axios'
import OpenVue from 'openvue/config'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { AuthorizationPrompt, AuthorizationRequest } from '@/features/oauth/api/oauth'
import OAuthAuthorizeView from '@/features/oauth/views/OAuthAuthorizeView.vue'

const inspectAuthorization = vi.fn<(request: AuthorizationRequest) => Promise<AuthorizationPrompt>>()
const decideAuthorization =
  vi.fn<(request: AuthorizationRequest, approve: boolean, permissions: string[]) => Promise<string>>()
const grantConsent = vi.fn<() => Promise<unknown>>()

vi.mock('@/features/oauth/api/oauth', () => ({
  inspectAuthorization: (request: AuthorizationRequest) => inspectAuthorization(request),
  decideAuthorization: (request: AuthorizationRequest, approve: boolean, permissions: string[]) =>
    decideAuthorization(request, approve, permissions),
}))

vi.mock('@/features/account/api/account', () => ({
  grantConsent: () => grantConsent(),
}))

const QUERY =
  '?client_id=cuisine_oc_1&response_type=code&code_challenge=abc&code_challenge_method=S256&state=xyz'

function prompt(overrides: Partial<AuthorizationPrompt> = {}): AuthorizationPrompt {
  return {
    client_name: 'ChatGPT',
    client_uri: null,
    redirect_host: 'chatgpt.com',
    offered: ['use:mcp', 'write:recipes', 'write:ingredients'],
    requested: ['use:mcp', 'write:recipes', 'write:ingredients'],
    error_redirect: null,
    ...overrides,
  }
}

function failure(status: number, code: string): AxiosError {
  const headers = new AxiosHeaders()
  return new AxiosError('failed', String(status), undefined, undefined, {
    status,
    statusText: '',
    headers,
    config: { headers },
    data: { detail: 'The app asked to return to an address it did not register.', code },
  })
}

async function mountAt(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/oauth/authorize', name: 'oauthAuthorize', component: OAuthAuthorizeView },
    ],
  })
  await router.push(path)
  const wrapper = mount(OAuthAuthorizeView, { global: { plugins: [router, i18n, OpenVue] } })
  await flushPromises()
  return wrapper
}

const assign = vi.fn<(url: string) => void>()

describe('OAuthAuthorizeView', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'enGB'
    inspectAuthorization.mockReset()
    decideAuthorization.mockReset()
    grantConsent.mockReset()
    assign.mockReset()
    vi.stubGlobal('location', { ...window.location, assign })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows who asks and where it returns to', async () => {
    inspectAuthorization.mockResolvedValue(prompt())
    const wrapper = await mountAt(`/oauth/authorize${QUERY}`)

    expect(inspectAuthorization).toHaveBeenCalledWith({
      client_id: 'cuisine_oc_1',
      response_type: 'code',
      code_challenge: 'abc',
      code_challenge_method: 'S256',
      state: 'xyz',
    })
    expect(wrapper.text()).toContain('ChatGPT wants to connect to your cookbook')
    expect(wrapper.text()).toContain('Returns to chatgpt.com')
    expect(wrapper.text()).toContain('Create recipe drafts')
  })

  it('sends the choice and follows the answer back to the app', async () => {
    inspectAuthorization.mockResolvedValue(prompt({ requested: ['use:mcp', 'write:recipes'] }))
    decideAuthorization.mockResolvedValue('https://chatgpt.com/cb?code=c&state=xyz')
    const wrapper = await mountAt(`/oauth/authorize${QUERY}`)

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(decideAuthorization).toHaveBeenCalledWith(expect.objectContaining({ client_id: 'cuisine_oc_1' }), true, [
      'use:mcp',
      'write:recipes',
    ])
    expect(assign).toHaveBeenCalledWith('https://chatgpt.com/cb?code=c&state=xyz')
  })

  it('declines', async () => {
    inspectAuthorization.mockResolvedValue(prompt())
    decideAuthorization.mockResolvedValue('https://chatgpt.com/cb?error=access_denied')
    const wrapper = await mountAt(`/oauth/authorize${QUERY}`)

    const decline = wrapper.findAll('button').find((b) => b.text() === 'Decline')
    await decline?.trigger('click')
    await flushPromises()

    expect(decideAuthorization).toHaveBeenCalledWith(expect.anything(), false, expect.any(Array))
    expect(assign).toHaveBeenCalledWith('https://chatgpt.com/cb?error=access_denied')
  })

  it('reports a broken request back to the app at once', async () => {
    inspectAuthorization.mockResolvedValue(prompt({ error_redirect: 'https://chatgpt.com/cb?error=invalid_request' }))
    await mountAt(`/oauth/authorize${QUERY}`)

    expect(assign).toHaveBeenCalledWith('https://chatgpt.com/cb?error=invalid_request')
  })

  it('shows an untrusted target instead of following it', async () => {
    inspectAuthorization.mockRejectedValue(failure(422, 'OAuthRedirectRejectedError'))
    const wrapper = await mountAt(`/oauth/authorize${QUERY}`)

    expect(wrapper.text()).toContain('did not register')
    expect(assign).not.toHaveBeenCalled()
  })

  it('asks for the AI agents consent first and then continues', async () => {
    inspectAuthorization.mockRejectedValueOnce(failure(403, 'ConsentRequiredError')).mockResolvedValue(prompt())
    grantConsent.mockResolvedValue([])
    const wrapper = await mountAt(`/oauth/authorize${QUERY}`)
    expect(wrapper.text()).toContain('Consent for AI agents')

    const agree = wrapper.findAll('button').find((b) => b.text() === 'Agree and continue')
    await agree?.trigger('click')
    await flushPromises()

    expect(grantConsent).toHaveBeenCalled()
    expect(wrapper.text()).toContain('ChatGPT wants to connect to your cookbook')
  })

  it('says so when the link names no app', async () => {
    const wrapper = await mountAt('/oauth/authorize?response_type=code')
    expect(inspectAuthorization).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('This link is incomplete')
  })
})
