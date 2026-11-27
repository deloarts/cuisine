import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import Tooltip from 'openvue/tooltip'
import { beforeEach, describe, expect, it } from 'vitest'

import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import PermissionChecklist from '@/features/admin-settings/components/PermissionChecklist.vue'

function mountList(permissions: string[], inherited = new Map<string, string[]>()) {
  return mount(PermissionChecklist, {
    props: { idPrefix: 'p', labelledby: 'caption', inherited, permissions },
    global: { plugins: [i18n, OpenVue], directives: { tooltip: Tooltip } },
  })
}

function checkbox(wrapper: ReturnType<typeof mountList>, perm: string): HTMLInputElement {
  return wrapper.get(`#p-${perm.replace(':', '-')}`).element as HTMLInputElement
}

describe('PermissionChecklist', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    useCurrentUserStore().user = {
      is_systemuser: false,
      effective_permissions: ['write:recipes', 'manage:recipes', 'write:users'],
    } as never
  })

  it('groups the permissions by area', () => {
    const wrapper = mountList([])
    expect(wrapper.findAll('h3').map((h) => h.text())).toEqual([
      'Recipes',
      'Ingredients and catalogue',
      'Tokens and agents',
      'Administration',
    ])
  })

  it('shows what a group grants checked and disabled', () => {
    const wrapper = mountList([], new Map([['write:recipes', ['Cooks']]]))
    expect(checkbox(wrapper, 'write:recipes').checked).toBe(true)
    expect(checkbox(wrapper, 'write:recipes').disabled).toBe(true)
    expect(wrapper.text()).toContain('Granted by Cooks.')
    expect(wrapper.find('[data-testid="drop-direct-write:recipes"]').exists()).toBe(false)
  })

  it('drops a direct grant that a group also gives', async () => {
    const wrapper = mountList(['write:recipes', 'write:users'], new Map([['write:recipes', ['Cooks']]]))
    await wrapper.get('[data-testid="drop-direct-write:recipes"]').trigger('click')
    expect(wrapper.emitted('update:permissions')!.at(-1)).toEqual([['write:users']])
  })

  it('locks what the editor does not hold', () => {
    const wrapper = mountList(['use:mcp'])
    expect(checkbox(wrapper, 'use:mcp').disabled).toBe(true)
    expect(checkbox(wrapper, 'use:mcp').checked).toBe(true)
    expect(checkbox(wrapper, 'write:users').disabled).toBe(false)
  })
})
