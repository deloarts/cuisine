/** The Notifications tab's mail endpoints: provider settings, test mail, alerts and templates. */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type MailSettings = Schemas['MailSettingsResponse']
export type MailSettingsRequest = Schemas['MailSettingsRequest']
export type MailTemplateKind = Schemas['MailTemplateKind']
export type MailTemplateGroup = Schemas['MailTemplateKindResponse']
export type MailTemplateText = Schemas['MailTemplateTextSchema']
export type MailAlert = Schemas['AlertResponse']
export type ContentLocale = Schemas['ContentLocale']

export const MAIL_LOCALES: ContentLocale[] = ['de-AT', 'en-GB']

export const getMailSettings = (): Promise<MailSettings> => webApi.get('/settings/mail')

export const saveMailSettings = (body: MailSettingsRequest): Promise<MailSettings> =>
  webApi.put('/settings/mail', { body })

export const sendTestMail = (to: string | null): Promise<unknown> =>
  webApi.post('/settings/mail/test', { body: { to } })

export const getMailAlerts = (): Promise<MailAlert[]> => webApi.get('/settings/mail/alerts')

export const getMailTemplates = (): Promise<MailTemplateGroup[]> => webApi.get('/settings/mail/templates')

/** Saves the given locales of one kind; a blank body goes back to the built-in default. */
export const saveMailTemplates = (kind: MailTemplateKind, texts: Record<string, MailTemplateText>): Promise<void> =>
  webApi.put('/settings/mail/templates/{kind}', { path: { kind }, body: texts })

export const previewMailTemplate = (kind: MailTemplateKind, text: MailTemplateText) =>
  webApi.post('/settings/mail/templates/{kind}/preview', { path: { kind }, body: text })

export const defaultMailTemplate = (kind: MailTemplateKind, locale: ContentLocale) =>
  webApi.get('/settings/mail/templates/{kind}/default', { path: { kind }, query: { locale } })

/** Uploads one template file; the backend takes its `<title>` as the subject. */
export function importMailTemplate(kind: MailTemplateKind, locale: ContentLocale, file: Blob, name: string): Promise<void> {
  const form = new FormData()
  form.append('locale', locale)
  form.append('file', file, name)
  return webApi.post('/settings/mail/templates/{kind}/import', { path: { kind }, body: form })
}
