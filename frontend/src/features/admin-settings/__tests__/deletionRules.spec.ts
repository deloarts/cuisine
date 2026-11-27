import { describe, expect, it } from 'vitest'

import {
  canDelete,
  defaultForm,
  deletionQuery,
  keepAllowed,
  needsOwnerChoice,
  needsVisibilityChoice,
  normaliseForm,
  recipeTotal,
  type DeletionImpact,
} from '@/features/admin-settings/deletionRules'

function impact(extra: Partial<DeletionImpact> = {}): DeletionImpact {
  return {
    recipes: { private: 0, household: 0, shared: 0, instance: 0, public: 0 },
    drafts: 0,
    ingredients: 0,
    lists_handed_over: 0,
    lists_deleted: 0,
    in_household: false,
    backup_keep_days: 14,
    backups_clear_by: '2026-12-05',
    ...extra,
  }
}

const readableOnly = impact({ recipes: { private: 0, household: 0, shared: 1, instance: 3, public: 0 } })
const withPrivate = impact({ recipes: { private: 2, household: 1, shared: 0, instance: 3, public: 0 } })

describe('the owner question', () => {
  it('is asked only when there are recipes or ingredients to hand over', () => {
    expect(needsOwnerChoice(impact())).toBe(false)
    expect(needsOwnerChoice(impact({ ingredients: 1 }))).toBe(true)
    expect(recipeTotal(withPrivate)).toBe(6)
  })

  it('sends no options when there is nothing to hand over', () => {
    expect(deletionQuery(defaultForm(), impact({ drafts: 4 }))).toEqual({})
  })

  it('needs a chosen person for a transfer', () => {
    expect(deletionQuery(defaultForm(), readableOnly)).toBeNull()
    expect(deletionQuery({ ...defaultForm(), newOwnerId: 'anna' }, readableOnly)).toEqual({ new_owner_id: 'anna' })
  })
})

describe('the visibility of ownerless recipes', () => {
  const nobody = { owner: 'nobody', newOwnerId: 'ignored', visibility: 'keep' } as const

  it('may stay as it is only without private and household recipes', () => {
    expect(keepAllowed(readableOnly)).toBe(true)
    expect(keepAllowed(withPrivate)).toBe(false)
    expect(deletionQuery(nobody, readableOnly)).toEqual({ ownerless_visibility: 'keep' })
    expect(deletionQuery(nobody, withPrivate)).toBeNull()
  })

  it('moves a forbidden keep to instance and leaves the other choices alone', () => {
    expect(normaliseForm(nobody, withPrivate).visibility).toBe('instance')
    expect(normaliseForm({ ...nobody, visibility: 'delete' }, withPrivate).visibility).toBe('delete')
    expect(normaliseForm(nobody, readableOnly).visibility).toBe('keep')
  })

  it('is only asked when nobody takes over recipes', () => {
    expect(needsVisibilityChoice(nobody, readableOnly)).toBe(true)
    expect(needsVisibilityChoice(defaultForm(), readableOnly)).toBe(false)
    expect(needsVisibilityChoice(nobody, impact({ ingredients: 2 }))).toBe(false)
  })
})

describe('canDelete', () => {
  it('waits for a complete form and the e-mail address', () => {
    const form = { ...defaultForm(), newOwnerId: 'anna' }
    const mail = 'ben@example.com'
    expect(canDelete(form, readableOnly, mail, mail)).toBe(true)
    expect(canDelete(form, readableOnly, ' Ben@Example.com ', mail)).toBe(true)
    expect(canDelete(form, readableOnly, 'ben', mail)).toBe(false)
    expect(canDelete(defaultForm(), readableOnly, mail, mail)).toBe(false)
  })
})
