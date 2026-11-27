/**
 * What the shell shows every signed-in user: the active banner (public, so
 * the login page could show it too) and the dialog notices this user has
 * not acknowledged yet.
 */
import { publicApi } from '@/core/api/auth'
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type BannerSeverity = Schemas['BannerSeverity']
export type PendingNotice = Schemas['NoticeResponse']

export type PublicBanner = Schemas['PublicBannerResponse']

type ContentLocale = Schemas['ContentLocale']

export async function getBanner(locale: ContentLocale): Promise<PublicBanner | null> {
  return (await publicApi.get<PublicBanner | null>('/banner', { params: { locale } })).data
}

export const getPendingNotices = (locale: ContentLocale): Promise<PendingNotice[]> =>
  webApi.get('/notices/pending', { query: { locale } })

export async function acknowledgeNotice(id: string): Promise<void> {
  await webApi.post('/notices/{notice_id}/acknowledge', { path: { notice_id: id } })
}
