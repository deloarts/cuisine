import { beforeEach, describe, expect, it } from 'vitest'

import {
  forgetPasskey,
  forgetRememberedAccount,
  listRememberedAccounts,
  rememberAccount,
  rememberSignedInAccount,
  updateRememberedAccount,
} from '@/features/auth/utils/rememberedAccounts'
import type { CurrentUserResponse } from '@/core/types/user'

const anna = { userId: 'u-anna', login: 'anna@example.com', displayName: 'Anna' }
const ben = { userId: 'u-ben', login: 'ben@example.com', displayName: 'Ben' }

describe('rememberedAccounts', () => {
  beforeEach(() => localStorage.clear())

  it('lists the most recent sign-in first and keeps one entry per account', async () => {
    rememberAccount(anna)
    await new Promise((resolve) => setTimeout(resolve, 2))
    rememberAccount(ben)
    await new Promise((resolve) => setTimeout(resolve, 2))
    rememberAccount({ ...anna, displayName: 'Anna B.' })
    expect(listRememberedAccounts().map((a) => a.displayName)).toEqual(['Anna B.', 'Ben'])
  })

  it('keeps the passkey of a later password sign-in', () => {
    rememberAccount({ ...anna, credentialId: 'cred-1', passkeyPublicId: 'pk-1' })
    rememberAccount(anna)
    expect(listRememberedAccounts()[0]).toMatchObject({ credentialId: 'cred-1', passkeyPublicId: 'pk-1' })
  })

  it('forgets a removed passkey and a forgotten account', () => {
    rememberAccount(anna)
    updateRememberedAccount(anna.userId, { credentialId: 'cred-1', passkeyPublicId: 'pk-1' })
    forgetPasskey('pk-1')
    expect(listRememberedAccounts()[0]).toMatchObject({ credentialId: null, passkeyPublicId: null })
    forgetRememberedAccount(anna.userId)
    expect(listRememberedAccounts()).toEqual([])
  })

  it('drops entries it cannot trust', () => {
    localStorage.setItem('cuisine.rememberedAccounts', JSON.stringify([{ login: 'x' }, 'junk']))
    expect(listRememberedAccounts()).toEqual([])
    localStorage.setItem('cuisine.rememberedAccounts', '{not json')
    expect(listRememberedAccounts()).toEqual([])
  })

  it('remembers the system user under the name it signs in with', async () => {
    const user = { id: 'u-sys', email: 'root@example.com', display_name: 'System', is_systemuser: true, avatar_id: null }
    await rememberSignedInAccount(user as unknown as CurrentUserResponse)
    expect(listRememberedAccounts()[0]).toMatchObject({ userId: 'u-sys', login: 'system' })
  })

  it('takes a new passkey without the public id of the one registered before', async () => {
    rememberAccount({ ...anna, credentialId: 'cred-1', passkeyPublicId: 'pk-1' })
    const user = { id: anna.userId, email: anna.login, display_name: 'Anna', is_systemuser: false, avatar_id: null }
    await rememberSignedInAccount(user as unknown as CurrentUserResponse, 'cred-2')
    expect(listRememberedAccounts()[0]).toMatchObject({ credentialId: 'cred-2', passkeyPublicId: null })
  })
})
