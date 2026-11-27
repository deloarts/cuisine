/**
 * The resource calls the tabs and their deletion dialogs make, kept in one
 * module so their specs can mock them.
 */
import type { Schemas } from '@/core/api/generated'
import { webApi, type WebRequestOptions } from '@/core/api/webRequest'

export type UnitDeletionImpact = Schemas['UnitDeletionImpact']

type UnitForm = WebRequestOptions<'/units', 'post'>['body']
type TagForm = WebRequestOptions<'/tags', 'post'>['body']
type CategoryForm = WebRequestOptions<'/ingredient-categories', 'post'>['body']
type FamilyForm = WebRequestOptions<'/ingredient-families', 'post'>['body']

/** Creates a unit, or updates it when an id is given. */
export const saveUnit = (id: string | null, body: UnitForm) =>
  id ? webApi.put('/units/{unit_id}', { path: { unit_id: id }, body }) : webApi.post('/units', { body })

/** Creates a tag, or updates it when an id is given. */
export const saveTag = (id: string | null, body: TagForm) =>
  id ? webApi.put('/tags/{tag_id}', { path: { tag_id: id }, body }) : webApi.post('/tags', { body })

export const deleteTag = (id: string) => webApi.delete('/tags/{tag_id}', { path: { tag_id: id } })

/** Creates an ingredient category, or updates it when an id is given. */
export const saveCategory = (id: string | null, body: CategoryForm) =>
  id
    ? webApi.put('/ingredient-categories/{category_id}', { path: { category_id: id }, body })
    : webApi.post('/ingredient-categories', { body })

/** Creates an ingredient family, or updates it when an id is given. */
export const saveFamily = (id: string | null, body: FamilyForm) =>
  id
    ? webApi.put('/ingredient-families/{family_id}', { path: { family_id: id }, body })
    : webApi.post('/ingredient-families', { body })

export const deleteFamily = (id: string) =>
  webApi.delete('/ingredient-families/{family_id}', { path: { family_id: id } })

export const unitDeletionImpact = (id: string): Promise<UnitDeletionImpact> =>
  webApi.get('/units/{unit_id}/deletion-impact', { path: { unit_id: id } })

export const mergeUnit = (id: string, intoId: string) =>
  webApi.post('/units/{unit_id}/merge', { path: { unit_id: id }, body: { into_id: intoId } })

export const deleteUnit = (id: string) => webApi.delete('/units/{unit_id}', { path: { unit_id: id } })

export const deleteCategory = (id: string, replacementId: string | null) =>
  webApi.delete('/ingredient-categories/{category_id}', {
    path: { category_id: id },
    query: { replacement_id: replacementId },
  })

export type EquipmentDeletionImpact = Schemas['EquipmentDeletionImpact']
export type EquipmentRequest = Schemas['EquipmentRequest']
export type EquipmentResponse = Schemas['EquipmentResponse']
export type DuplicateCandidate = Schemas['DuplicateCandidate']

export const listEquipment = (): Promise<EquipmentResponse[]> => webApi.get('/equipment')

export const createEquipment = (body: EquipmentRequest): Promise<EquipmentResponse> =>
  webApi.post('/equipment', { body })

export const updateEquipment = (id: string, body: EquipmentRequest): Promise<EquipmentResponse> =>
  webApi.put('/equipment/{equipment_id}', { path: { equipment_id: id }, body })

export const activateEquipment = (id: string) =>
  webApi.post('/equipment/{equipment_id}/activate', { path: { equipment_id: id } })

export const equipmentDuplicates = (name: string, locale: 'en-GB' | 'de-AT'): Promise<DuplicateCandidate[]> =>
  webApi.get('/equipment/duplicates', { query: { name, locale } })

export const equipmentDeletionImpact = (id: string): Promise<EquipmentDeletionImpact> =>
  webApi.get('/equipment/{equipment_id}/deletion-impact', { path: { equipment_id: id } })

export const mergeEquipment = (id: string, intoId: string) =>
  webApi.post('/equipment/{equipment_id}/merge', { path: { equipment_id: id }, body: { into_id: intoId } })

export const deleteEquipment = (id: string) =>
  webApi.delete('/equipment/{equipment_id}', { path: { equipment_id: id } })

export type ResourceUsageResponse = Schemas['ResourceUsageResponse']

export const resourceUsage = (): Promise<ResourceUsageResponse> => webApi.get('/resources/usage')
