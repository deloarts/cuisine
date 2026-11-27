/** The admin's instance API keys: listing, creating and revoking them. */
import type { Schemas } from '@/core/api/generated'
import { webApi, type WebRequestOptions } from '@/core/api/webRequest'

export type ApiKey = Schemas['ApiKeyResponse']
export type ApiKeyForm = WebRequestOptions<'/api-keys', 'post'>['body']

export const listApiKeys = () => webApi.get('/api-keys')

export const createApiKey = (body: ApiKeyForm) => webApi.post('/api-keys', { body })

export async function revokeApiKey(id: string): Promise<void> {
  await webApi.delete('/api-keys/{key_id}', { path: { key_id: id } })
}
