import { ref } from 'vue'
import { defineStore } from 'pinia'

import { publicApi } from '@/core/api/auth'
import type { Schemas } from '@/core/api/generated'
import { i18n, type AppLocale } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { setDisplayFormats } from '@/core/utils/displayFormats'

type PublicInfoResponse = Schemas['PublicInfoResponse']

/**
 * The instance name, default language and display defaults, readable before
 * sign-in. Loading it also sets the date formats and the week start, and,
 * while nobody is signed in, the UI language to the instance's default, so
 * the sign-in page speaks the household's language.
 */
export const usePublicInfoStore = defineStore('publicInfo', () => {
  const info = ref<PublicInfoResponse | null>(null)

  async function fetch(): Promise<void> {
    try {
      info.value = (await publicApi.get<PublicInfoResponse>('/info')).data
      setDisplayFormats({
        date_format: info.value.date_format,
        time_format: info.value.time_format,
        first_day_of_week: info.value.first_day_of_week,
      })
      if (!useCurrentUserStore().user) {
        i18n.global.locale.value = info.value.default_language as AppLocale
      }
    } catch {
      info.value = null
    }
  }

  return { info, fetch }
})
