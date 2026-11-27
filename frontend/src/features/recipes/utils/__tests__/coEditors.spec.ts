import { describe, expect, it } from 'vitest'

import { coEditorCandidates, coEditorSuggestions } from '@/features/recipes/utils/coEditors'

const owner = { id: 'owner', display_name: 'Olga' }
const anna = { id: 'anna', display_name: 'Anna' }
const ben = { id: 'ben', display_name: 'Ben' }
const zoe = { id: 'zoe', display_name: 'Zoe' }
const everyone = [owner, zoe, ben, anna]
const household = [owner, zoe]

describe('co-editor candidates', () => {
  it('offers everybody but the owner for a public recipe, household members first', () => {
    const list = coEditorCandidates({ visibility: 'instance', ownerId: 'owner', everyone, household, sharedUserIds: [] })
    expect(list.map((p) => p.id)).toEqual(['zoe', 'anna', 'ben'])
  })

  it('limits a household recipe to the household and a shared one to its people', () => {
    expect(
      coEditorCandidates({ visibility: 'household', ownerId: 'owner', everyone, household, sharedUserIds: [] }).map((p) => p.id),
    ).toEqual(['zoe'])
    expect(
      coEditorCandidates({ visibility: 'shared', ownerId: 'owner', everyone, household, sharedUserIds: ['ben'] }).map((p) => p.id),
    ).toEqual(['ben'])
  })

  it('offers everybody but the owner for a public recipe too', () => {
    const list = coEditorCandidates({ visibility: 'public', ownerId: 'owner', everyone, household, sharedUserIds: [] })
    expect(list.map((p) => p.id)).toEqual(['zoe', 'anna', 'ben'])
  })

  it('offers everybody but the owner for a recipe for paired instances', () => {
    const list = coEditorCandidates({ visibility: 'peers', ownerId: 'owner', everyone, household, sharedUserIds: [] })
    expect(list.map((p) => p.id)).toEqual(['zoe', 'anna', 'ben'])
  })

  it('offers nobody for a private recipe', () => {
    expect(coEditorCandidates({ visibility: 'private', ownerId: 'owner', everyone, household, sharedUserIds: [] })).toEqual([])
  })

  it('suggests household members not chosen yet', () => {
    const list = coEditorCandidates({ visibility: 'instance', ownerId: 'owner', everyone, household, sharedUserIds: [] })
    expect(coEditorSuggestions(list, household, []).map((p) => p.id)).toEqual(['zoe'])
    expect(coEditorSuggestions(list, household, ['zoe'])).toEqual([])
  })
})
