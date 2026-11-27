import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import type { RecipeVisibility } from '@/features/recipes/api/recipes'
import VisibilityPicker from '@/features/recipes/components/VisibilityPicker.vue'

vi.mock('@/features/recipes/api/recipes', () => ({
  listGroups: () => Promise.resolve([]),
}))

async function mountPicker(visibility: RecipeVisibility, publicAllowed: boolean) {
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(VisibilityPicker, {
    props: { visibility, sharedUserIds: [], sharedGroupIds: [], publicAllowed },
    global: { plugins: [i18n, OpenVue], stubs: { UserPicker: true, MultiSelect: true } },
  })
  await flushPromises()
  return wrapper
}

const levels = (wrapper: Awaited<ReturnType<typeof mountPicker>>) =>
  wrapper.findAll('input[name="visibility"]').map((input) => input.attributes('id'))

describe('VisibilityPicker', () => {
  it('offers the ladder without public while public recipes are not allowed', async () => {
    const wrapper = await mountPicker('instance', false)
    expect(levels(wrapper)).toEqual([
      'visibility-private',
      'visibility-household',
      'visibility-shared',
      'visibility-instance',
    ])
    expect(wrapper.find('[data-testid="public-limited"]').exists()).toBe(false)
  })

  it('offers public last while public recipes are allowed', async () => {
    const wrapper = await mountPicker('instance', true)
    expect(levels(wrapper).at(-1)).toBe('visibility-public')
  })

  it('keeps a stored public and says it reads as instance while not allowed', async () => {
    const wrapper = await mountPicker('public', false)
    expect(levels(wrapper)).toContain('visibility-public')
    expect(wrapper.find('[data-testid="public-limited"]').text()).toContain('only signed-in users')
  })
})

const MultiSelectStub = {
  name: 'MultiSelect',
  props: ['modelValue', 'options'],
  emits: ['update:modelValue'],
  template: '<div />',
}

describe('VisibilityPicker with paired instances', () => {
  const peers = [
    { id: 'p1', name: 'Friends' },
    { id: 'p2', name: 'Family' },
  ]

  async function mountShared(props: Record<string, unknown>) {
    i18n.global.locale.value = 'enGB'
    const wrapper = mount(VisibilityPicker, {
      props: {
        visibility: 'shared' as RecipeVisibility,
        sharedUserIds: [],
        sharedGroupIds: [],
        publicAllowed: true,
        ...props,
      },
      global: { plugins: [i18n, OpenVue], stubs: { UserPicker: true, MultiSelect: MultiSelectStub } },
    })
    await flushPromises()
    return wrapper
  }

  it('offers the paired instances inside chosen people and saves the choice', async () => {
    const wrapper = await mountShared({ peerTargets: peers, sharedPeerIds: [] })
    const field = wrapper.get('[data-testid="share-peers"]')
    expect(field.text()).toContain('Paired instances')
    const picker = field.findComponent({ name: 'MultiSelect' })
    expect(picker.props('options')).toEqual(peers)
    picker.vm.$emit('update:modelValue', ['p2'])
    expect(wrapper.emitted('update:sharedPeerIds')).toEqual([[['p2']]])
  })

  it('hides the instances while there are none to pick', async () => {
    const wrapper = await mountShared({ peerTargets: [] })
    expect(wrapper.find('[data-testid="share-peers"]').exists()).toBe(false)
  })

  it('warns when sub-recipes do not go to every chosen instance', async () => {
    const wrapper = await mountShared({ peerTargets: peers, sharedPeerIds: ['p1'], peerHiddenNames: 'Teig' })
    expect(wrapper.get('[data-testid="peer-hidden-sub-recipes"]').text()).toContain('Teig')
    const none = await mountShared({ peerTargets: peers, sharedPeerIds: [], peerHiddenNames: 'Teig' })
    expect(none.find('[data-testid="peer-hidden-sub-recipes"]').exists()).toBe(false)
  })

  it('offers neither public nor instances for a copy of a recipe from another instance', async () => {
    const wrapper = await mountShared({ peerTargets: peers, capped: true })
    expect(levels(wrapper)).not.toContain('visibility-public')
    expect(wrapper.find('[data-testid="share-peers"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="visibility-capped"]').text()).toContain('stays on this cookbook')
  })
})

describe('VisibilityPicker with the paired instances level', () => {
  async function mountPeers(visibility: RecipeVisibility, props: Record<string, unknown>) {
    i18n.global.locale.value = 'enGB'
    const wrapper = mount(VisibilityPicker, {
      props: { visibility, sharedUserIds: [], sharedGroupIds: [], publicAllowed: true, ...props },
      global: { plugins: [i18n, OpenVue], stubs: { UserPicker: true, MultiSelect: true } },
    })
    await flushPromises()
    return wrapper
  }

  it('offers paired instances between everyone here and public while peering is on', async () => {
    const wrapper = await mountPeers('instance', { peering: true })
    expect(levels(wrapper).slice(-3)).toEqual([
      'visibility-instance',
      'visibility-peers',
      'visibility-public',
    ])
    expect(wrapper.text()).toContain('every paired cookbook')
  })

  it('hides paired instances while peering is off', async () => {
    const wrapper = await mountPeers('instance', { peering: false })
    expect(levels(wrapper)).not.toContain('visibility-peers')
  })

  it('keeps a stored paired instances level and says it reads as instance while peering is off', async () => {
    const wrapper = await mountPeers('peers', { peering: false })
    expect(levels(wrapper)).toContain('visibility-peers')
    expect(wrapper.get('[data-testid="peers-limited"]').text()).toContain('Peering is switched off')
  })

  it('never offers paired instances for a copy of a recipe from another instance', async () => {
    const wrapper = await mountPeers('instance', { peering: true, capped: true })
    expect(levels(wrapper)).not.toContain('visibility-peers')
    expect(levels(wrapper)).not.toContain('visibility-public')
  })
})
