/** The admin area's read-outs and one-off actions: households, the log, the recipe export and reference updates. */
import { webApi, type QueryOf, type WebRequestOptions } from '@/core/api/webRequest'

export type AdminLogQuery = QueryOf<'/admin/logs'>
export type RecipeExportQuery = QueryOf<'/admin/recipes/export'>
export type AcceptReferenceUpdateBody = WebRequestOptions<'/admin/reference-updates/accept', 'post'>['body']

export const adminApi = {
  households: () => webApi.get('/admin/households'),
  logs: (query: AdminLogQuery) => webApi.get('/admin/logs', { query }),
  exportRecipes: async (query: RecipeExportQuery): Promise<Blob> =>
    (await webApi.get('/admin/recipes/export', { query, config: { responseType: 'blob' } })) as Blob,
  referenceUpdates: () => webApi.get('/admin/reference-updates'),
  acceptReferenceUpdate: async (body: AcceptReferenceUpdateBody) => {
    await webApi.post('/admin/reference-updates/accept', { body })
  },
}
