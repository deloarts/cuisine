import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Schemas } from '@/core/api/generated'
import { i18n } from '@/core/i18n'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import PeeringAcceptView from '@/features/peering/views/PeeringAcceptView.vue'

const CODE = 'cuisine_pi_abc123'

async function mountAt(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/login', name: 'login', component: { template: '<div />' } },
      { path: '/peering/accept', name: 'peering-accept', component: PeeringAcceptView },
    ],
  })
  await router.push(path)
  const wrapper = mount(PeeringAcceptView, { global: { plugins: [router, i18n, OpenVue, ToastService] } })
  await flushPromises()
  return wrapper
}

describe('PeeringAcceptView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
  })

  it('names this instance and explains where to paste the link', async () => {
    usePublicInfoStore().info = { instance_name: 'Kitchen A' } as Schemas['PublicInfoResponse']
    const wrapper = await mountAt(`/peering/accept?code=${CODE}`)

    expect(wrapper.text()).toContain('connect your Cuisine with Kitchen A')
    expect(wrapper.text()).toContain('Administration → Peers → Accept an invitation')
    const field = wrapper.find('#peering-invitation-link')
    expect((field.element as HTMLInputElement).value).toBe(`${window.location.origin}/peering/accept?code=${CODE}`)
    expect(field.attributes('readonly')).toBeDefined()
  })

  it('copies the full link', async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    const wrapper = await mountAt(`/peering/accept?code=${CODE}`)

    await wrapper.find('button').trigger('click')
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/peering/accept?code=${CODE}`)
  })

  it('falls back to a neutral name without the public info', async () => {
    const wrapper = await mountAt(`/peering/accept?code=${CODE}`)

    expect(wrapper.text()).toContain('connect your Cuisine with this instance')
  })
})
