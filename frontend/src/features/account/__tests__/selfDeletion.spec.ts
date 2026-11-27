import { describe, expect, it } from 'vitest'

import {
  canDeleteOwn,
  deletionBody,
  emptyForm,
  offersPublicDeletion,
  refused,
  summarise,
  type SelfDeletionImpact,
} from '@/features/account/selfDeletion'

function impact(overrides: Partial<SelfDeletionImpact> = {}): SelfDeletionImpact {
  return {
    recipes_kept_online: 2,
    recipes_to_household: 1,
    recipes_deleted: 3,
    drafts_deleted: 1,
    recipes_handed_over: [],
    sub_recipes_kept_online: 0,
    if_public_deleted: { recipes_deleted: 5, drafts_deleted: 1, recipes_handed_over: [], sub_recipes_kept_online: 0 },
    can_delete_public_recipes: true,
    ingredients_kept: 4,
    lists_handed_over: 0,
    lists_deleted: 1,
    in_household: true,
    refused_reason: null,
    backup_keep_days: 14,
    backups_clear_by: '2026-12-06',
    ...overrides,
  }
}

const passkey = { challenge_token: 'c', credential: { id: 'x' } }

describe('selfDeletion', () => {
  it('sorts the impact into what stays online, what is handed over and what is deleted', () => {
    expect(summarise(impact(), false)).toEqual({
      staysOnline: [
        { key: 'recipesOnline', count: 2 },
        { key: 'ingredientsKept', count: 4 },
      ],
      handedOver: [{ key: 'recipesToHousehold', count: 1 }],
      deleted: [
        { key: 'recipesDeleted', count: 3 },
        { key: 'draftsDeleted', count: 1 },
        { key: 'listsDeleted', count: 1 },
      ],
    })
  })

  it('lists the recipes handed over to the owners of the recipes using them', () => {
    const pesto = { id: 'p', title: 'Pesto', new_owner_name: 'Cook' }
    const summary = summarise(impact({ recipes_handed_over: [pesto], lists_handed_over: 1 }), false)
    expect(summary.handedOver).toEqual([
      { key: 'recipesToHousehold', count: 1 },
      { key: 'recipesHandedOver', count: 1, recipes: [pesto] },
      { key: 'listsHandedOver', count: 1 },
    ])
  })

  it('takes the fates for the chosen option, hand-overs of public recipes included', () => {
    const pesto = { id: 'p', title: 'Pesto', new_owner_name: 'Cook' }
    const summary = summarise(
      impact({
        sub_recipes_kept_online: 2,
        if_public_deleted: { recipes_deleted: 4, drafts_deleted: 0, recipes_handed_over: [pesto], sub_recipes_kept_online: 0 },
      }),
      true,
    )
    expect(summary.staysOnline).toEqual([{ key: 'ingredientsKept', count: 4 }])
    expect(summary.handedOver).toContainEqual({ key: 'recipesHandedOver', count: 1, recipes: [pesto] })
    expect(summary.deleted).toEqual([
      { key: 'recipesDeleted', count: 4 },
      { key: 'listsDeleted', count: 1 },
    ])
    expect(summarise(impact({ sub_recipes_kept_online: 2 }), false).staysOnline).toContainEqual({
      key: 'subRecipesKept',
      count: 2,
    })
  })

  it('moves the public recipes to the deleted ones when the user chooses so', () => {
    const summary = summarise(impact(), true)
    expect(summary.staysOnline).toEqual([{ key: 'ingredientsKept', count: 4 }])
    expect(summary.deleted[0]).toEqual({ key: 'recipesDeleted', count: 5 })
  })

  it('offers deleting the public recipes only when the instance allows it and there are some', () => {
    expect(offersPublicDeletion(impact())).toBe(true)
    expect(offersPublicDeletion(impact({ can_delete_public_recipes: false }))).toBe(false)
    expect(offersPublicDeletion(impact({ recipes_kept_online: 0 }))).toBe(false)
  })

  it('ignores the choice where it is not offered', () => {
    const locked = impact({ can_delete_public_recipes: false })
    expect(summarise(locked, true).staysOnline[0]).toEqual({ key: 'recipesOnline', count: 2 })
    const form = { ...emptyForm(), deletePublic: true, password: 'pw', typed: 'cook' }
    expect(deletionBody(locked, form).delete_public_recipes).toBe(false)
    expect(deletionBody(impact(), form).delete_public_recipes).toBe(true)
  })

  it('deletes only after re-authentication and the own e-mail address', () => {
    const mail = 'cook@example.com'
    const base = { ...emptyForm(), typed: mail }
    expect(canDeleteOwn(impact(), base, mail)).toBe(false)
    expect(canDeleteOwn(impact(), { ...base, password: 'pw' }, mail)).toBe(true)
    expect(canDeleteOwn(impact(), { ...base, passkey }, mail)).toBe(true)
    expect(canDeleteOwn(impact(), { ...base, password: 'pw', typed: 'cook' }, mail)).toBe(false)
    expect(canDeleteOwn(impact(), { ...base, password: 'pw', typed: ' Cook@Example.com ' }, mail)).toBe(true)
  })

  it('refuses the last admin and the system user whatever the form says', () => {
    const lastAdmin = impact({ refused_reason: 'last_admin' })
    expect(refused(lastAdmin)).toBe(true)
    expect(canDeleteOwn(lastAdmin, { ...emptyForm(), password: 'pw', typed: 'cook@example.com' }, 'cook@example.com')).toBe(false)
  })

  it('sends the passkey instead of a password typed as well', () => {
    const body = deletionBody(impact(), { ...emptyForm(), password: 'pw', passkey, typed: ' cook@example.com ' })
    expect(body).toEqual({ email: 'cook@example.com', password: null, passkey, delete_public_recipes: false })
  })
})
