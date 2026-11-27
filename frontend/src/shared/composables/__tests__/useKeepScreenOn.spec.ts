import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { useKeepScreenOn } from '@/shared/composables/useKeepScreenOn'

const request = vi.fn<() => Promise<void>>(() => Promise.resolve())
const release = vi.fn<() => Promise<void>>(() => Promise.resolve())
vi.mock('@vueuse/core', () => ({
  useWakeLock: () => ({ isSupported: ref(true), isActive: ref(false), request, release }),
}))

const Page = defineComponent({
  setup() {
    useKeepScreenOn()
    return () => h('div')
  },
})

describe('useKeepScreenOn', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockClear()
    release.mockClear()
  })

  it('keeps the screen on while the page is open and lets go when it closes', async () => {
    useCurrentUserStore().user = { keep_screen_on: true } as never
    const wrapper = mount(Page)
    expect(request).toHaveBeenCalledWith('screen')
    wrapper.unmount()
    expect(release).toHaveBeenCalled()
  })

  it('follows the account setting', async () => {
    const store = useCurrentUserStore()
    store.user = { keep_screen_on: false } as never
    const wrapper = mount(Page)
    expect(request).not.toHaveBeenCalled()

    store.user = { keep_screen_on: true } as never
    await flushPromises()
    expect(request).toHaveBeenCalledTimes(1)
    store.user = { keep_screen_on: false } as never
    await flushPromises()
    expect(release).toHaveBeenCalled()
    wrapper.unmount()
  })
})
