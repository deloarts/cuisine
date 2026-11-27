import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { PeerSuggestionRequest } from '@/features/admin-settings/api/peering'
import AdminPeerSuggestionsSection from '@/features/admin-settings/components/AdminPeerSuggestionsSection.vue'
import type { PeerSuggestionGroup } from '@/features/admin-settings/peerSuggestions'

const list = vi.fn<(query: Record<string, string>) => Promise<PeerSuggestionGroup[]>>()
const accept = vi.fn<(body: PeerSuggestionRequest) => Promise<void>>()
const dismiss = vi.fn<(body: PeerSuggestionRequest) => Promise<void>>()

vi.mock('@/features/admin-settings/api/peering', () => ({
  peeringApi: { list: () => Promise.resolve([{ id: 'p1', name: 'Friends', status: 'active' }]) },
  suggestionsApi: {
    list: (query: Record<string, string>) => list(query),
    accept: (body: PeerSuggestionRequest) => accept(body),
    dismiss: (body: PeerSuggestionRequest) => dismiss(body),
  },
}))

const peer = { id: 'p1', name: 'Friends' }
const kren: PeerSuggestionGroup = {
  kind: 'ingredient',
  id: 'i1',
  name: 'Kren',
  warning: true,
  suggestions: [
    { peer, source_id: 's1', field: 'allergens', current: [], suggested: ['mustard'], unmapped_units: [] },
    { peer, source_id: 's1', field: 'conversions', current: {}, suggested: { tbsp: 15 }, unmapped_units: ['scoop'] },
  ],
}

async function open(path = '/admin') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/admin', component: { render: () => null } }],
  })
  await router.push(path)
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(AdminPeerSuggestionsSection, {
    global: { plugins: [router, i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

// The row actions sit in a context menu; on the narrow test screen a button
// at the end of the row opens it.
async function openRowMenu(rowText: string): Promise<HTMLElement[]> {
  const row = [...document.body.querySelectorAll('tr')].find((tr) => tr.textContent?.includes(rowText))!
  row.querySelector<HTMLButtonElement>('button[aria-label="Row actions"]')!.click()
  await flushPromises()
  return [...document.body.querySelectorAll<HTMLElement>('[role="menuitem"]')]
}

function menuItem(items: HTMLElement[], label: string): HTMLElement {
  return items.find((item) => item.getAttribute('aria-label')?.startsWith(label))!.firstElementChild as HTMLElement
}

describe('AdminPeerSuggestionsSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useCurrentUserStore().user = {
      id: 'me',
      is_systemuser: false,
      effective_permissions: ['read:settings', 'manage:ingredients', 'write:ingredients'],
    } as never
    list.mockResolvedValue([kren])
    accept.mockResolvedValue()
    dismiss.mockResolvedValue()
  })
  afterEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('lists warnings first with labels and the units left out, filtered by the URL', async () => {
    const wrapper = await open('/admin?sugPeer=p1&sugKind=ingredient')
    expect(list).toHaveBeenCalledWith({ peer_id: 'p1', kind: 'ingredient' })
    const text = document.body.textContent ?? ''
    expect(text).toContain('Warnings')
    expect(text.indexOf('Allergens')).toBeLessThan(text.indexOf('Conversions to grams'))
    expect(text).toContain('tbsp: 15')
    expect(text).toContain('Left out, no unit here: scoop')
    wrapper.unmount()
  })

  it('accepts a value and loads again, and dismisses a row', async () => {
    const wrapper = await open()
    menuItem(await openRowMenu('Allergens'), 'Accept the suggested value of Allergens').click()
    await flushPromises()
    expect(accept).toHaveBeenCalledWith({ peer_id: 'p1', kind: 'ingredient', source_id: 's1', field: 'allergens' })
    expect(list).toHaveBeenCalledTimes(2)

    menuItem(await openRowMenu('Conversions'), 'Dismiss the suggested value of Conversions').click()
    await flushPromises()
    expect(dismiss).toHaveBeenCalledWith({ peer_id: 'p1', kind: 'ingredient', source_id: 's1', field: 'conversions' })
    expect(document.body.textContent).not.toContain('tbsp: 15')
    wrapper.unmount()
  })

  it('offers no decision without the rights of the kind', async () => {
    useCurrentUserStore().user = { id: 'me', is_systemuser: false, effective_permissions: ['read:settings'] } as never
    const wrapper = await open()
    expect(document.body.textContent).toContain('Kren')
    expect(await openRowMenu('Allergens')).toHaveLength(0)
    wrapper.unmount()
  })
})
