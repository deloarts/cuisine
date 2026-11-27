/** The admin side of webhooks and dialog notices. */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type WebhookEvent = Schemas['WebhookEventResponse']
export type WebhookSubscription = Schemas['WebhookSubscriptionResponse']
export type WebhookDelivery = Schemas['WebhookDeliveryResponse']
export type WebhookForm = Schemas['WebhookSubscriptionRequest']
export type AdminNotice = Schemas['NoticeAdminResponse']
export type NoticeText = Schemas['NoticeTextResponse']
export type AcknowledgementOverview = Schemas['AcknowledgementOverviewResponse']

type NoticeBody = Schemas['NoticeRequest']

export const webhooksApi = {
  events: () => webApi.get('/admin/webhooks/events'),
  list: () => webApi.get('/admin/webhooks'),
  create: (body: WebhookForm) => webApi.post('/admin/webhooks', { body }),
  update: (id: string, body: WebhookForm) =>
    webApi.put('/admin/webhooks/{webhook_id}', { path: { webhook_id: id }, body }),
  remove: async (id: string) => {
    await webApi.delete('/admin/webhooks/{webhook_id}', { path: { webhook_id: id } })
  },
  rotateSecret: (id: string) => webApi.post('/admin/webhooks/{webhook_id}/rotate-secret', { path: { webhook_id: id } }),
  test: (id: string) => webApi.post('/admin/webhooks/{webhook_id}/test', { path: { webhook_id: id } }),
  deliveries: (id: string, limit: number, offset: number) =>
    webApi.get('/admin/webhooks/{webhook_id}/deliveries', { path: { webhook_id: id }, query: { limit, offset } }),
  retry: (id: string, deliveryId: string) =>
    webApi.post('/admin/webhooks/{webhook_id}/deliveries/{delivery_id}/retry', {
      path: { webhook_id: id, delivery_id: deliveryId },
    }),
}

export const noticesApi = {
  list: () => webApi.get('/admin/notices'),
  create: (body: NoticeBody) => webApi.post('/admin/notices', { body }),
  update: (id: string, body: NoticeBody) => webApi.put('/admin/notices/{notice_id}', { path: { notice_id: id }, body }),
  remove: async (id: string) => {
    await webApi.delete('/admin/notices/{notice_id}', { path: { notice_id: id } })
  },
  acknowledgements: (id: string) =>
    webApi.get('/admin/notices/{notice_id}/acknowledgements', { path: { notice_id: id } }),
}
