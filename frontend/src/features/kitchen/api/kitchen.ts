/**
 * The calls of "My kitchen": the kitchen itself (the household's or the
 * user's own), setting it up, saving the ticked items, forgetting it, and
 * the equipment catalogue to tick from.
 */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type Kitchen = Schemas['KitchenResponse']
export type EquipmentResponse = Schemas['EquipmentResponse']

export const getKitchen = (): Promise<Kitchen> => webApi.get('/kitchen')

export const setUpKitchen = (ids: string[]): Promise<Kitchen> =>
  webApi.post('/kitchen/setup', { body: { equipment_ids: ids } })

export const saveKitchen = (ids: string[]): Promise<Kitchen> => webApi.put('/kitchen', { body: { equipment_ids: ids } })

export const forgetKitchen = () => webApi.delete('/kitchen')

export const listEquipment = (): Promise<EquipmentResponse[]> => webApi.get('/equipment')
