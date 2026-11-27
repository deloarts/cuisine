/**
 * The published legal pages, readable without a session, and the user's
 * answer to the blocking privacy statement.
 */
import { publicApi } from '@/core/api/auth'
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type LegalPage = Schemas['LegalPageResponse']
export type LegalPageKind = 'imprint' | 'privacy'

/** The current version of a legal page in the given content language. */
export async function getLegalPage(kind: LegalPageKind, locale: string): Promise<LegalPage> {
  return (await publicApi.get<LegalPage>(`/legal/${kind}`, { params: { locale } })).data
}

export function acknowledgePrivacy(version: number): Promise<void> {
  return webApi.post('/users/me/privacy/acknowledge', { body: { version } })
}

/** Declines the statement; the backend ends the session. */
export function declinePrivacy(): Promise<void> {
  return webApi.post('/users/me/privacy/decline')
}
