/**
 * The labels of catalogue kinds and fields and the readable text of field
 * values, in the current language, shared by the reference data updates and
 * the catalogue file import, whose rows use the same field names.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { fieldName, formatValue, type ValueLabels } from '@/features/admin-settings/referenceUpdates'

export function useCatalogueFieldLabels() {
  const { t, te, locale } = useI18n()

  const monthFormat = computed(
    () => new Intl.DateTimeFormat(locale.value === 'deAT' ? 'de-AT' : 'en-GB', { month: 'short' }),
  )
  const labels = computed<ValueLabels>(() => ({
    marker: (field, key) => {
      const id = field === 'allergens' ? `allergens.${key}` : `dietMarkers.${key}`
      return te(id) ? t(id) : key
    },
    month: (m) => monthFormat.value.format(new Date(2000, m - 1, 1)),
    yes: t('common.yes'),
    no: t('referenceUpdates.no'),
    empty: '–',
  }))

  function kindLabel(kind: string): string {
    const id = `referenceUpdates.kinds.${kind}`
    return te(id) ? t(id) : kind
  }

  function fieldLabel(field: string): string {
    const name = fieldName(field)
    if (!name.known) return field
    return t(`referenceUpdates.fields.${name.base}`, { detail: name.detail ?? '' })
  }

  function valueText(field: string, value: unknown): string {
    return formatValue(field, value, labels.value)
  }

  return { kindLabel, fieldLabel, valueText }
}
