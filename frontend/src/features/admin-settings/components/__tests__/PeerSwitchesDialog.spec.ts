import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import type { IncomingRecipe, Peer, PeerSwitches } from '@/features/admin-settings/api/peering'
import PeerSwitchesDialog from '@/features/admin-settings/components/PeerSwitchesDialog.vue'

const saveSwitches = vi.fn<(id: string, body: PeerSwitches) => Promise<Peer>>()
const acceptWaiting = vi.fn<(id: string) => Promise<{ accepted: number }>>()
const pending = vi.fn<() => Promise<IncomingRecipe[]>>()

vi.mock('@/features/admin-settings/api/peering', () => ({
  peeringApi: {
    saveSwitches: (id: string, body: PeerSwitches) => saveSwitches(id, body),
    acceptWaiting: (id: string) => acceptWaiting(id),
  },
  incomingApi: { list: () => pending() },
}))

// The confirm dialog itself lives in the app shell; the spec answers it.
const confirmMessages: string[] = []
const confirmAnswer = vi.fn<() => boolean>(() => true)
vi.mock('openvue/useconfirm', () => ({
  useConfirm: () => ({
    require: (options: { message: string; accept?: () => void; reject?: () => void }) => {
      confirmMessages.push(options.message)
      return confirmAnswer() ? options.accept?.() : options.reject?.()
    },
  }),
}))

const peer = {
  id: 'p1',
  name: 'Friends',
  users_may_share: true,
  accept_incoming: true,
  mirror_visibility: 'instance',
  mirror_group: null,
  sync_all: false,
} as Peer

const waiting = (peerId: string) => ({ id: `w-${peerId}`, peer: { id: peerId, name: 'x' } }) as IncomingRecipe

async function open() {
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(PeerSwitchesDialog, {
    props: { peer, groups: [] },
    global: { plugins: [i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

async function switchSyncAllOnAndSave() {
  const toggle = document.body.querySelector<HTMLInputElement>('#peer-sync-all')!
  toggle.click()
  await flushPromises()
  document.body.querySelector<HTMLFormElement>('.switches-form')!.requestSubmit()
  await flushPromises()
}

describe('PeerSwitchesDialog', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    confirmMessages.length = 0
    confirmAnswer.mockReset().mockReturnValue(true)
    saveSwitches.mockReset().mockImplementation((_id, body) => Promise.resolve({ ...peer, ...body } as Peer))
    acceptWaiting.mockReset().mockResolvedValue({ accepted: 2 })
    pending.mockReset().mockResolvedValue([waiting('p1'), waiting('p1'), waiting('other')])
  })

  it('has no switch for sending all public recipes and saves sync all', async () => {
    const wrapper = await open()
    expect(document.body.querySelector('#peer-send-all-public')).toBeNull()
    expect(document.body.textContent).toContain('Sync all from this instance')
    await switchSyncAllOnAndSave()
    expect(saveSwitches).toHaveBeenCalledWith('p1', expect.objectContaining({ sync_all: true }))
    expect(wrapper.emitted('saved')).toHaveLength(1)
    wrapper.unmount()
  })

  it('offers once to accept what waits from this peer when sync all goes on', async () => {
    const wrapper = await open()
    await switchSyncAllOnAndSave()
    expect(confirmMessages).toHaveLength(1)
    expect(confirmMessages[0]).toContain('2 recipes from Friends are waiting')
    expect(acceptWaiting).toHaveBeenCalledWith('p1')
    wrapper.unmount()
  })

  it('accepts nothing when the admin declines or nothing waits', async () => {
    confirmAnswer.mockReturnValue(false)
    const declined = await open()
    await switchSyncAllOnAndSave()
    expect(acceptWaiting).not.toHaveBeenCalled()
    declined.unmount()

    confirmMessages.length = 0
    pending.mockResolvedValue([waiting('other')])
    const empty = await open()
    await switchSyncAllOnAndSave()
    expect(confirmMessages).toHaveLength(0)
    empty.unmount()
  })
})
