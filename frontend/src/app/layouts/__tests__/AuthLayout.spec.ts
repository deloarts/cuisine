import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import AuthLayout from '@/app/layouts/AuthLayout.vue'
import type { Schemas } from '@/core/api/generated'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'

function withBackground(key: string | null) {
  const store = usePublicInfoStore()
  store.info = { login_background_key: key } as Schemas['PublicInfoResponse']
  return store
}

function mountLayout() {
  return mount(AuthLayout, { global: { stubs: { RouterView: true, SteamBackdrop: true } } })
}

describe('AuthLayout', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows the glow and no photo when none is set', () => {
    withBackground(null)
    const wrapper = mountLayout()

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.auth-glow').exists()).toBe(true)
  })

  it('keeps the photo hidden until it has loaded, then fades it in', async () => {
    withBackground('abc123')
    const wrapper = mountLayout()
    const photo = wrapper.find('.auth-photo')

    expect(wrapper.find('img').attributes('src')).toBe('/api/v1/public/branding/login-background?v=abc123')
    expect(wrapper.find('.auth-glow').exists()).toBe(false)
    expect(photo.classes()).not.toContain('loaded')

    await wrapper.find('img').trigger('load')
    expect(photo.classes()).toContain('loaded')
  })

  it('starts from black again when the photo changes', async () => {
    const store = withBackground('first')
    const wrapper = mountLayout()
    await wrapper.find('img').trigger('load')

    store.info = { login_background_key: 'second' } as Schemas['PublicInfoResponse']
    await wrapper.vm.$nextTick()

    expect(wrapper.find('img').attributes('src')).toContain('v=second')
    expect(wrapper.find('.auth-photo').classes()).not.toContain('loaded')
  })

  it('shows the steam only while the administrator has it on', async () => {
    const store = usePublicInfoStore()
    store.info = { login_background_key: null, login_steam: true } as Schemas['PublicInfoResponse']
    const wrapper = mountLayout()
    expect(wrapper.findComponent({ name: 'SteamBackdrop' }).exists()).toBe(true)

    store.info = { login_background_key: null, login_steam: false } as Schemas['PublicInfoResponse']
    await wrapper.vm.$nextTick()
    expect(wrapper.findComponent({ name: 'SteamBackdrop' }).exists()).toBe(false)
  })
})
