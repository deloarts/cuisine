import { AxiosError, AxiosHeaders } from 'axios'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { IncomingRecipe, MappingDecision } from '@/features/admin-settings/api/peering'
import IncomingRecipeDialog from '@/features/admin-settings/components/IncomingRecipeDialog.vue'
import MappingDecisionFields from '@/features/admin-settings/components/MappingDecisionFields.vue'

const accept = vi.fn<(id: string, decisions: MappingDecision[]) => Promise<{ id: string; title: string }>>()

vi.mock('@/features/admin-settings/api/peering', () => ({
  incomingApi: { accept: (id: string, decisions: MappingDecision[]) => accept(id, decisions) },
}))

function item(overrides: Partial<IncomingRecipe> = {}): IncomingRecipe {
  const base = { names: {}, category_suggestion: null, allergens: [], diet_markers: [] }
  return {
    id: 'in1',
    peer: { id: 'p1', name: 'Friends' },
    source_id: 'src1',
    title: 'Krenfleisch',
    description: '',
    author_name: 'Mia',
    status: 'pending',
    kind: 'new',
    mirror_id: null,
    received_at: '2026-11-22T10:00:00Z',
    decided_at: null,
    entries: [
      { ...base, kind: 'ingredient', source_id: 'kren', name: 'Kren', suggestion: { id: 'local-kren', name: 'Kren' }, allergens: ['mustard'] },
      { ...base, kind: 'equipment', source_id: 'moerser', name: 'Mörser', suggestion: null },
      { ...base, kind: 'tag', source_id: 'deftig', name: 'deftig', suggestion: null },
    ],
    sub_recipes: [],
    ...overrides,
  }
}

async function open(incoming: IncomingRecipe) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/recipes/:id', name: 'recipe', component: { template: '<div />' } }],
  })
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(IncomingRecipeDialog, {
    props: { item: incoming },
    global: { plugins: [router, i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

const acceptButton = () => document.body.querySelector<HTMLButtonElement>('[data-testid="incoming-accept"]')!
const entryRow = (key: string) => document.body.querySelector<HTMLElement>(`[data-testid="entry-${key}"]`)!

describe('IncomingRecipeDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts every entry at its suggestion and sends the decisions', async () => {
    accept.mockResolvedValue({ id: 'm1', title: 'Krenfleisch' })
    const wrapper = await open(item())
    expect(document.body.textContent).toContain('by Mia · Friends')
    expect(document.body.textContent).toContain('Allergens: Mustard')

    acceptButton().click()
    await flushPromises()

    expect(accept).toHaveBeenCalledWith('in1', [
      { kind: 'ingredient', source_id: 'kren', action: 'map', target_id: 'local-kren', category_id: null },
      { kind: 'equipment', source_id: 'moerser', action: 'create', target_id: null, category_id: null },
      { kind: 'tag', source_id: 'deftig', action: 'none', target_id: null, category_id: null },
    ])
    expect(wrapper.emitted('accepted')?.[0]?.[1]).toEqual({ id: 'm1', title: 'Krenfleisch' })
    wrapper.unmount()
  })

  it('sends a changed decision and marks a map without a target before asking', async () => {
    const wrapper = await open(item())
    const fields = wrapper.findAllComponents(MappingDecisionFields)
    const tag = fields.find((f) => f.props('kind') === 'tag')!
    tag.vm.$emit('update:modelValue', { action: 'create', target_id: null, target_name: null, category_id: null })
    const equipment = fields.find((f) => f.props('kind') === 'equipment')!
    equipment.vm.$emit('update:modelValue', { action: 'map', target_id: null, target_name: null, category_id: null })
    await flushPromises()

    acceptButton().click()
    await flushPromises()

    expect(accept).not.toHaveBeenCalled()
    expect(entryRow('equipment:moerser').dataset.missing).toBe('true')
    expect(entryRow('tag:deftig').dataset.missing).toBeUndefined()

    equipment.vm.$emit('update:modelValue', { action: 'plain', target_id: null, target_name: null, category_id: null })
    accept.mockResolvedValue({ id: 'm1', title: 'Krenfleisch' })
    await flushPromises()
    acceptButton().click()
    await flushPromises()
    expect(accept.mock.calls[0]![1]).toContainEqual({
      kind: 'tag',
      source_id: 'deftig',
      action: 'create',
      target_id: null,
      category_id: null,
    })
    wrapper.unmount()
  })

  it('marks the entries the backend still finds missing', async () => {
    const config = { headers: new AxiosHeaders() }
    accept.mockRejectedValue(
      new AxiosError('x', 'ERR', config, null, {
        status: 422,
        statusText: '',
        headers: {},
        config,
        data: { code: 'PeerMappingError', detail: 'Decide every entry.', missing: ['tag:deftig'] },
      }),
    )
    const wrapper = await open(item())
    acceptButton().click()
    await flushPromises()
    expect(entryRow('tag:deftig').dataset.missing).toBe('true')
    expect(entryRow('tag:deftig').textContent).toContain('still needs a decision')
    expect(wrapper.emitted('accepted')).toBeUndefined()
    wrapper.unmount()
  })

  it('explains a held update and links the mirror it updates', async () => {
    const wrapper = await open(item({ kind: 'update', mirror_id: 'm1', entries: [] }))
    expect(document.body.querySelector('[data-testid="incoming-held-update"]')!.textContent).toContain('previous version')
    expect(document.body.querySelector('[data-testid="incoming-no-entries"]')).not.toBeNull()
    wrapper.unmount()
  })
})
