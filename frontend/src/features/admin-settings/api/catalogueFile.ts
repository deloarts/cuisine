/**
 * The catalogue file: exporting the whole catalogue as one JSON file, and
 * importing such a file in two steps, a preview that writes nothing and the
 * import that creates the new entries and writes the accepted differences.
 */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type CataloguePreview = Schemas['CataloguePreviewResponse']
export type CataloguePreviewEntry = Schemas['CataloguePreviewEntryResponse']
export type CatalogueImportReport = Schemas['CatalogueImportResponse']
export type CatalogueKind = CataloguePreviewEntry['kind']

/** What the file picker accepts. */
export const CATALOGUE_FILE_TYPES = '.json,application/json'

export async function exportCatalogue(): Promise<Blob> {
  const data = await webApi.get('/admin/catalogue/export', { config: { responseType: 'blob' } })
  return data as Blob
}

export function previewCatalogueImport(file: File): Promise<CataloguePreview> {
  const body = new FormData()
  body.append('file', file)
  return webApi.post('/admin/catalogue/import/preview', { body })
}

/** `accept` holds the differences to write as `<kind>:<source id>:<field>`. */
export function importCatalogue(file: File, accept: string[]): Promise<CatalogueImportReport> {
  const body = new FormData()
  body.append('file', file)
  for (const key of accept) body.append('accept', key)
  return webApi.post('/admin/catalogue/import', { body })
}
