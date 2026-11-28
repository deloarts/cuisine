import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import Tooltip from 'openvue/tooltip'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import AccountProfileTab from '@/features/account/components/AccountProfileTab.vue'

const patch = vi.fn<(path: string, options: { body: Record<string, unknown> }) => Promise<unknown>>()

vi.mock('@/features/account/api/account', () => ({
  uploadAvatar: vi.fn<() => void>(),
  removeAvatar: vi.fn<() => void>(),
  updateProfile: (body: Record<string, unknown>) => patch('/users/me', { body }),
}))

const me = {
  id: 'me',
  full_name: 'Anna Cook',
  nickname: null,
  show_nickname: false,
  display_name: 'Anna Cook',
  email: 'anna@example.com',
  language: 'enGB',
  theme_preset: 'Aura',
  theme_primary: 'cuisine',
  theme_surface: 'neutral',
  theme_dark_mode: false,
  recipe_show_tips: true,
  recipe_show_notes: true,
  recipe_show_cooked: false,
  recipe_show_rating: true,
  recipe_highlight_mentions: true,
  keep_screen_on: true,
  cook_mode_layout: 'step',
  avatar_id: null,
  effective_permissions: [],
  is_systemuser: false,
}

function mountTab() {
  return mount(AccountProfileTab, {
    global: { plugins: [i18n, OpenVue, ToastService], directives: { tooltip: Tooltip } },
  })
}

describe('AccountProfileTab recipe cards', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    useCurrentUserStore().user = { ...me } as never
  })

  it('shows a switch per card, set from the profile', () => {
    const wrapper = mountTab()
    const cards = wrapper.get('[data-testid="recipe-cards"]')
    expect(cards.findAll('label').map((l) => l.text())).toEqual(['Tips', 'My notes', 'Cooked', 'Rating'])
    const checked = (id: string) => (wrapper.get(`#profile-${id}`).element as HTMLInputElement).checked
    expect(checked('recipe_show_tips')).toBe(true)
    expect(checked('recipe_show_cooked')).toBe(false)
  })

  it('saves switched cards on their own, sending only what changed', async () => {
    patch.mockImplementation((_path, options) => Promise.resolve({ ...me, ...options.body }))
    // Applying the answer would switch the real theme, which jsdom cannot.
    const apply = vi.spyOn(useCurrentUserStore(), 'apply').mockImplementation(() => {})
    const wrapper = mountTab()
    await wrapper.get('#profile-recipe_show_notes').setValue(false)
    await wrapper.get('#profile-recipe_show_cooked').setValue(true)
    // The switches go out together a moment after the last change, with no save button.
    await new Promise((resolve) => setTimeout(resolve, 300))
    await flushPromises()

    expect(wrapper.find('button[type="submit"]').exists()).toBe(false)
    expect(patch).toHaveBeenCalledTimes(1)
    expect(patch.mock.calls[0]![0]).toBe('/users/me')
    expect(patch.mock.calls[0]![1].body).toEqual({ recipe_show_notes: false, recipe_show_cooked: true })
    expect(apply).toHaveBeenCalledTimes(1)
  })

  it('saves a text field when the user leaves it, not while typing', async () => {
    patch.mockImplementation((_path, options) => Promise.resolve({ ...me, ...options.body }))
    vi.spyOn(useCurrentUserStore(), 'apply').mockImplementation(() => {})
    const wrapper = mountTab()
    const name = wrapper.get('#profile-name')
    await name.setValue('Anna Köchin')
    await new Promise((resolve) => setTimeout(resolve, 300))
    await flushPromises()
    expect(patch).not.toHaveBeenCalled()

    await name.trigger('blur')
    await flushPromises()
    expect(patch).toHaveBeenCalledTimes(1)
    expect(patch.mock.calls[0]![1].body).toEqual({ full_name: 'Anna Köchin' })
  })
})

describe('AccountProfileTab mention highlighting', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    useCurrentUserStore().user = { ...me } as never
  })

  it('shows the setting from the profile and saves it when turned off', async () => {
    patch.mockImplementation((_path, options) => Promise.resolve({ ...me, ...options.body }))
    vi.spyOn(useCurrentUserStore(), 'apply').mockImplementation(() => {})
    const wrapper = mountTab()
    const toggle = wrapper.get('#profile-recipe_highlight_mentions')
    expect((toggle.element as HTMLInputElement).checked).toBe(true)

    await toggle.setValue(false)
    await new Promise((resolve) => setTimeout(resolve, 300))
    await flushPromises()
    expect(patch.mock.calls.at(-1)![1].body).toMatchObject({ recipe_highlight_mentions: false })
  })

  it('saves the keep-the-screen-on switch on its own', async () => {
    patch.mockImplementation((_path, options) => Promise.resolve({ ...me, ...options.body }))
    vi.spyOn(useCurrentUserStore(), 'apply').mockImplementation(() => {})
    const wrapper = mountTab()
    const toggle = wrapper.get('#profile-keep_screen_on')
    expect((toggle.element as HTMLInputElement).checked).toBe(true)

    await toggle.setValue(false)
    await new Promise((resolve) => setTimeout(resolve, 300))
    await flushPromises()
    expect(patch.mock.calls.at(-1)![1].body).toEqual({ keep_screen_on: false })
  })

  it('saves the cook mode layout', async () => {
    patch.mockImplementation((_path, options) => Promise.resolve({ ...me, ...options.body }))
    vi.spyOn(useCurrentUserStore(), 'apply').mockImplementation(() => {})
    const wrapper = mountTab()
    const select = wrapper
      .findAllComponents({ name: 'Select' })
      .find((c) => c.attributes('id') === 'profile-cook-mode-layout')!
    expect(select.props('modelValue')).toBe('step')

    select.vm.$emit('update:modelValue', 'flow')
    await new Promise((resolve) => setTimeout(resolve, 300))
    await flushPromises()
    expect(patch.mock.calls.at(-1)![1].body).toEqual({ cook_mode_layout: 'flow' })
  })
})

describe('AccountProfileTab nickname', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    useCurrentUserStore().user = { ...me } as never
    patch.mockReset()
  })

  it('offers the switch only once a nickname is typed', async () => {
    const wrapper = mountTab()
    const toggle = () => wrapper.get('#profile-show-nickname').element as HTMLInputElement
    expect(toggle().disabled).toBe(true)
    await wrapper.get('#profile-nickname').setValue('Bubu')
    expect(toggle().disabled).toBe(false)
  })

  it('saves the nickname and the choice to show it', async () => {
    patch.mockImplementation((_path, options) => Promise.resolve({ ...me, ...options.body }))
    vi.spyOn(useCurrentUserStore(), 'apply').mockImplementation(() => {})
    const wrapper = mountTab()
    await wrapper.get('#profile-nickname').setValue('Bubu')
    await wrapper.get('#profile-show-nickname').setValue(true)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(patch.mock.calls[0]![1].body).toMatchObject({ nickname: 'Bubu', show_nickname: true })
  })
})

describe('AccountProfileTab e-mail', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    patch.mockReset()
  })

  it('saves a new sign-in address with the profile', async () => {
    useCurrentUserStore().user = { ...me } as never
    patch.mockImplementation((_path, options) => Promise.resolve({ ...me, ...options.body }))
    vi.spyOn(useCurrentUserStore(), 'apply').mockImplementation(() => {})
    const wrapper = mountTab()
    expect(wrapper.find('#profile-username').exists()).toBe(false)
    expect(wrapper.text()).toContain('You sign in with it.')
    await wrapper.get('#profile-email').setValue('chef.anna@example.com')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(patch.mock.calls[0]![1].body).toMatchObject({ email: 'chef.anna@example.com' })
  })
})
