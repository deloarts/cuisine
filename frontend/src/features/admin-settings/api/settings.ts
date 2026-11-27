/** The admin settings sections, each read and saved as a whole, plus the upload of the login background. */
import { webApi, type WebRequestOptions } from '@/core/api/webRequest'

type SaveBody<P extends string> = WebRequestOptions<P, 'put'>['body']

export const getBannerSettings = () => webApi.get('/settings/banner')
export const saveBannerSettings = (body: SaveBody<'/settings/banner'>) => webApi.put('/settings/banner', { body })

export const getFeatureSettings = () => webApi.get('/settings/features')
export const saveFeatureSettings = (body: SaveBody<'/settings/features'>) => webApi.put('/settings/features', { body })

export const getMaintenanceSettings = () => webApi.get('/settings/maintenance')
export const saveMaintenanceSettings = (body: SaveBody<'/settings/maintenance'>) =>
  webApi.put('/settings/maintenance', { body })

export const getRetentionSettings = () => webApi.get('/settings/retention')
export const saveRetentionSettings = (body: SaveBody<'/settings/retention'>) =>
  webApi.put('/settings/retention', { body })

export const getNotificationSettings = () => webApi.get('/settings/notifications')
export const saveNotificationSettings = (body: SaveBody<'/settings/notifications'>) =>
  webApi.put('/settings/notifications', { body })

export const getAgentSettings = () => webApi.get('/settings/agents')
export const saveAgentSettings = (body: SaveBody<'/settings/agents'>) => webApi.put('/settings/agents', { body })

export const getGeneralSettings = () => webApi.get('/settings/general')
export const saveGeneralSettings = (body: SaveBody<'/settings/general'>) => webApi.put('/settings/general', { body })

export const getIntegrationSettings = () => webApi.get('/settings/integrations')
export const saveIntegrationSettings = (body: SaveBody<'/settings/integrations'>) =>
  webApi.put('/settings/integrations', { body })

export const getPrivacySettings = () => webApi.get('/settings/privacy')
export const savePrivacySettings = (body: SaveBody<'/settings/privacy'>) => webApi.put('/settings/privacy', { body })

export const getSecuritySettings = () => webApi.get('/settings/security')
export const saveSecuritySettings = (body: SaveBody<'/settings/security'>) =>
  webApi.put('/settings/security', { body })

export const getShoppingSettings = () => webApi.get('/settings/shopping')
export const saveShoppingSettings = (body: SaveBody<'/settings/shopping'>) =>
  webApi.put('/settings/shopping', { body })

/** Uploads the login page's background image and returns the stored file. */
export function uploadLoginBackground(file: File) {
  const data = new FormData()
  data.append('file', file)
  return webApi.post('/files', { body: data })
}
