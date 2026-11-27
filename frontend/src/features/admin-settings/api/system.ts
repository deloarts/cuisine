/** The admin area's live readings of the machine and the storage. */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type HostStatus = Schemas['HostStatusResponse']
export type StorageStatus = Schemas['StorageStatusResponse']
export type RestoreStep = Schemas['RestoreStepResponse']

export const getHostStatus = (): Promise<HostStatus> => webApi.get('/admin/host')
export const getStorageStatus = (): Promise<StorageStatus> => webApi.get('/admin/storage')

export const requestBackup = (): Promise<unknown> => webApi.post('/admin/backups/run')

export const getRestoreGuidance = (locale: Schemas['ContentLocale']): Promise<RestoreStep[]> =>
  webApi.get('/admin/backups/restore-guidance', { query: { locale } })
