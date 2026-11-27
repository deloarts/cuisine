import { useToast } from 'openvue/usetoast'
import { useI18n } from 'vue-i18n'

import { errorMessage } from '@/core/utils/errors'

/** Success and error toasts with the app's defaults. */
export function useAppToast() {
  const toast = useToast()
  const { t } = useI18n()

  return {
    success(summary: string, detail?: string) {
      toast.add({ severity: 'success', summary, detail, life: 3000 })
    },
    error(error: unknown, fallbackKey = 'common.error') {
      toast.add({
        severity: 'error',
        summary: t('common.error'),
        detail: errorMessage(error, t(fallbackKey)),
        life: 6000,
      })
    },
  }
}
