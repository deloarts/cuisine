/**
 * The units, tags, ingredient categories and families, loaded once and shared by every
 * page that needs them (pickers, the ingredient editor, the shopping list).
 * The backend resolves their names in the user's language, so the cache is
 * dropped when the UI language changes, and `reload()` refreshes it after
 * the resources page changed something.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { listCategories, listFamilies, listTags, listUnits } from '@/shared/api/cookbook'

import type { CategoryResponse, FamilyResponse, TagResponse, UnitResponse } from './types'

const units = ref<UnitResponse[]>([])
const tags = ref<TagResponse[]>([])
const categories = ref<CategoryResponse[]>([])
const families = ref<FamilyResponse[]>([])
let pending: Promise<void> | null = null
let loadedFor: string | null = null

async function fetchAll() {
  ;[units.value, tags.value, categories.value, families.value] = await Promise.all([
    listUnits(),
    listTags(),
    listCategories(),
    listFamilies(),
  ])
}

export function useCookbookResources() {
  const { locale } = useI18n()

  function load(): Promise<void> {
    if (loadedFor === locale.value && pending) return pending
    loadedFor = locale.value
    pending = fetchAll().catch((err: unknown) => {
      pending = null
      loadedFor = null
      throw err
    })
    return pending
  }

  function reload(): Promise<void> {
    pending = null
    loadedFor = null
    return load()
  }

  watch(locale, () => {
    if (loadedFor !== null && loadedFor !== locale.value) void reload().catch(() => undefined)
  })

  return { units, tags, categories, families, load, reload }
}
