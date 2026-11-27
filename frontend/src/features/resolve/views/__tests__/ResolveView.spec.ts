import { flushPromises, mount } from '@vue/test-utils'
import { AxiosError, AxiosHeaders } from 'axios'
import OpenVue from 'openvue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { ResolvedPublicIdResponse } from '@/features/resolve/api/resolve'
import ResolveView from '@/features/resolve/views/ResolveView.vue'

const resolvePublicId = vi.fn<(id: string) => Promise<ResolvedPublicIdResponse>>()

vi.mock('@/features/resolve/api/resolve', () => ({
  resolvePublicId: (id: string) => resolvePublicId(id),
}))

function failure(status: number): AxiosError {
  const headers = new AxiosHeaders()
  return new AxiosError('failed', String(status), undefined, undefined, {
    status,
    statusText: '',
    headers,
    config: { headers },
    data: { detail: 'failed' },
  })
}

async function mountAt(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/recipes/:id', name: 'recipe', component: { template: '<div />' } },
      { path: '/r/:publicId', name: 'resolve', component: ResolveView },
    ],
  })
  await router.push(path)
  const wrapper = mount(ResolveView, { global: { plugins: [router, i18n, OpenVue] } })
  await flushPromises()
  return { wrapper, router }
}

describe('ResolveView', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'enGB'
  })

  it('replaces itself with the page the id opens', async () => {
    resolvePublicId.mockResolvedValue({ kind: 'variation', id: 'v1', route: '/recipes/r1?variation=v1' })
    const { router } = await mountAt('/r/v1')

    expect(resolvePublicId).toHaveBeenCalledWith('v1')
    expect(router.currentRoute.value.name).toBe('recipe')
    expect(router.currentRoute.value.params.id).toBe('r1')
    expect(router.currentRoute.value.query.variation).toBe('v1')
  })

  it('says the link leads nowhere when the id is unknown or hidden', async () => {
    resolvePublicId.mockRejectedValue(failure(404))
    const { wrapper, router } = await mountAt('/r/nope')

    expect(router.currentRoute.value.name).toBe('resolve')
    expect(wrapper.text()).toContain('This link leads nowhere')
    expect(wrapper.text()).toContain('To the start page')
  })

  it('never follows a route to another origin', async () => {
    resolvePublicId.mockResolvedValue({ kind: 'recipe', id: 'r1', route: '//evil.example/x' })
    const { wrapper, router } = await mountAt('/r/r1')

    expect(router.currentRoute.value.name).toBe('resolve')
    expect(wrapper.text()).toContain('This link leads nowhere')
  })

  it('tells a failure apart from a missing id', async () => {
    resolvePublicId.mockRejectedValue(failure(500))
    const { wrapper } = await mountAt('/r/r1')

    expect(wrapper.text()).toContain('could not be opened right now')
  })
})
