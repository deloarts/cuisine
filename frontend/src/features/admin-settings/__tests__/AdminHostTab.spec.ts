import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import AdminHostTab from '@/features/admin-settings/components/AdminHostTab.vue'
import type { HostStatus } from '@/features/admin-settings/api/system'

let answer: (status: HostStatus) => void = () => {}
vi.mock('@/features/admin-settings/api/system', () => ({
  getHostStatus: () => new Promise<HostStatus>((resolve) => (answer = resolve)),
}))

const status = {
  app_version: '1.2.3',
  hostname: 'kitchen',
  platform: 'Linux',
  python_version: '3.13.1',
  process_start_time: '2026-11-27T08:00:00Z',
  boot_time: '2026-11-20T08:00:00Z',
  cpu_count: 4,
  cpu_percent: 12,
  load_average: [0.5, 0.4, 0.3],
  memory_percent: 40,
  memory_used_bytes: 4e9,
  memory_total_bytes: 8e9,
  disk_path: '/',
  disk_percent: 50,
  disk_used_bytes: 5e10,
  disk_total_bytes: 1e11,
  services: [{ name: 'database', status: 'ok', version: '16', latency_ms: 2, detail: null }],
} as unknown as HostStatus

describe('AdminHostTab', () => {
  it('shows skeletons in place of the readings until they arrive', async () => {
    i18n.global.locale.value = 'enGB'
    const wrapper = mount(AdminHostTab, { global: { plugins: [i18n, OpenVue, ToastService] } })
    await flushPromises()
    expect(wrapper.findAll('[data-pc-name="skeleton"]').length).toBeGreaterThan(5)
    expect(wrapper.find('[data-pc-name="progressbar"]').exists()).toBe(false)

    answer(status)
    await flushPromises()
    expect(wrapper.find('[data-pc-name="skeleton"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('1.2.3')
    expect(wrapper.findAll('[data-pc-name="progressbar"]')).toHaveLength(3)
    wrapper.unmount()
  })
})
