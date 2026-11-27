import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'

import { guard } from '@/router'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { CurrentUserResponse } from '@/core/types/user'

function route(partial: Partial<RouteLocationNormalized>): RouteLocationNormalized {
  return { fullPath: '/', meta: {}, name: undefined, ...partial } as RouteLocationNormalized
}

function signIn(permissions: string[]) {
  useCurrentUserStore().user = {
    is_systemuser: false,
    effective_permissions: permissions,
  } as unknown as CurrentUserResponse
}

describe('router guard', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('sends a visitor without a session to the login page with a redirect', () => {
    expect(guard(route({ fullPath: '/account' }))).toEqual({
      name: 'login',
      query: { redirect: '/account' },
    })
  })

  it('lets anybody open the public pages', () => {
    expect(guard(route({ name: 'login', meta: { requiresAuth: false } }))).toBe(true)
  })

  it('sends a signed-in user away from the login page', () => {
    signIn([])
    expect(guard(route({ name: 'login', meta: { requiresAuth: false } }))).toEqual({ name: 'home' })
  })

  it('needs one of the page permissions', () => {
    signIn(['write:groups'])
    expect(guard(route({ meta: { permissions: ['write:users'] } }))).toEqual({ name: 'home' })
    expect(guard(route({ meta: { permissions: ['write:users', 'write:groups'] } }))).toBe(true)
  })
})
