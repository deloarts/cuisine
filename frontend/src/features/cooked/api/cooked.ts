/** The cooked calendar's calls: the cook events of a range and the directory for the person filter. */
import type { Schemas } from '@/core/api/generated'
import { webApi, type QueryOf, type WebRequestOptions } from '@/core/api/webRequest'

export type CookEvent = Schemas['CookEventResponse']
export type CookEventQuery = QueryOf<'/cook-events'>
export type CookEventCreate = NonNullable<WebRequestOptions<'/cook-events', 'post'>['body']>
export type CookEventUpdate = NonNullable<WebRequestOptions<'/cook-events/{event_id}', 'put'>['body']>

export const listCookEvents = (query: CookEventQuery): Promise<CookEvent[]> => webApi.get('/cook-events', { query })

export const createCookEvent = (body: CookEventCreate) => webApi.post('/cook-events', { body })

export const updateCookEvent = (id: string, body: CookEventUpdate) =>
  webApi.put('/cook-events/{event_id}', { path: { event_id: id }, body })

export const deleteCookEvent = (id: string) => webApi.delete('/cook-events/{event_id}', { path: { event_id: id } })

export const listPeople = () => webApi.get('/users/directory')
