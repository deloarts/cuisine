/** The admin side of the legal pages: their published versions, the privacy draft and publishing. */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

type LegalKind = Schemas['LegalKind']
type ContentLocale = Schemas['ContentLocale']

export const adminLegalApi = {
  versions: (kind: LegalKind) => webApi.get('/admin/legal/{kind}/versions', { path: { kind } }),
  privacyDraft: (locale: ContentLocale) => webApi.get('/admin/legal/privacy/draft', { query: { locale } }),
  publish: (kind: LegalKind, texts: Record<string, string>) =>
    webApi.post('/admin/legal/{kind}', { path: { kind }, body: { texts } }),
  privacyAcknowledgements: () => webApi.get('/admin/legal/privacy/acknowledgements'),
}
