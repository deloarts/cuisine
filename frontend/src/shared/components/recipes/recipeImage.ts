/**
 * The URL of a stored image. Images load straight from the backend, through
 * the same origin as the API, so the session cookie authorises them.
 */
const API_ROOT = import.meta.env.VITE_API_URL ?? ''

export type ImageVariant = 'thumbnail' | 'original'

export function imageUrl(fileId: string, variant: ImageVariant = 'thumbnail'): string {
  return `${API_ROOT}/api/v1/web/files/${encodeURIComponent(fileId)}/content?variant=${variant}`
}
