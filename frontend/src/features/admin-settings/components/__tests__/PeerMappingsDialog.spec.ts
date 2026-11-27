import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { MappingCorrection, Peer, PeerMapping } from '@/features/admin-settings/api/peering'
import MappingDecisionFields from '@/features/admin-settings/components/MappingDecisionFields.vue'
import PeerMappingsDialog from '@/features/admin-settings/components/PeerMappingsDialog.vue'

const mappings = vi.fn<() => Promise<PeerMapping[]>>()
const correct = vi.fn<(peer: string, kind: string, source: string, body: MappingCorrection) => Promise<PeerMapping>>()

vi.mock('@/features/admin-settings/api/peering', () => ({
  incomingApi: {
    mappings: () => mappings(),
    correct: (peer: string, kind: string, source: string, body: MappingCorrection) => correct(peer, kind, source, body),
  },
}))
vi.mock('@/core/api/webRequest', () => ({
  webApi: { get: () => Promise.resolve([]) },
}))

const kren: PeerMapping = {
  kind: 'ingredient',
  source_id: 'kren',
  name: 'Kren',
  action: 'map',
  target_id: 'local-kren',
  target_name: 'Meerrettich',
  created_here: true,
  matched_by: 'decision',
  used_by: 2,
  updated: '2026-11-22T10:00:00Z',
}

async function open() {
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(PeerMappingsDialog, {
    props: { peer: { id: 'p1', name: 'Friends' } as Peer },
    global: { plugins: [i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

describe('PeerMappingsDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useCurrentUserStore().user = { id: 'me', is_systemuser: false, effective_permissions: ['write:settings'] } as never
    mappings.mockResolvedValue([kren])
  })

  it('lists each mapping with its target, origin and use and says corrections apply everywhere', async () => {
    const wrapper = await open()
    const row = document.body.querySelector('[data-testid="mapping-ingredient:kren"]')!
    expect(row.textContent).toContain('uses "Meerrettich"')
    expect(row.textContent).toContain('created here')
    expect(row.textContent).toContain('in 2 recipes')
    expect(document.body.textContent).toContain('applies to every recipe from this instance')
    wrapper.unmount()
  })

  it('corrects a mapping and shows the new state', async () => {
    correct.mockResolvedValue({ ...kren, action: 'plain', target_id: null, target_name: null })
    const wrapper = await open()
    document.body.querySelector<HTMLButtonElement>('[data-testid="mapping-edit-ingredient:kren"]')!.click()
    await flushPromises()
    wrapper
      .findComponent(MappingDecisionFields)
      .vm.$emit('update:modelValue', { action: 'plain', target_id: 'local-kren', target_name: 'Meerrettich', category_id: null })
    await flushPromises()
    document.body.querySelector<HTMLButtonElement>('[data-testid="mapping-save"]')!.click()
    await flushPromises()

    expect(correct).toHaveBeenCalledWith('p1', 'ingredient', 'kren', {
      action: 'plain',
      target_id: null,
      category_id: null,
    })
    const row = document.body.querySelector('[data-testid="mapping-ingredient:kren"]')!
    expect(row.textContent).toContain('kept as plain text')
    wrapper.unmount()
  })
})
