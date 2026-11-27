/**
 * The resolver's call to the web API. The view imports from here, so a spec
 * mocks this module.
 */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type ResolvedPublicIdResponse = Schemas['ResolvedPublicIdResponse']

/** What a public id opens, if the reader may open it; 404 otherwise. */
export function resolvePublicId(publicId: string) {
  return webApi.get('/resolve/{public_id}', { path: { public_id: publicId } })
}
