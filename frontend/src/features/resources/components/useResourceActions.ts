/**
 * The save and delete plumbing the resource tabs share: a toast on
 * failure, a confirmation before deleting, and a reload of the shared
 * resource cache afterwards so pickers elsewhere see the change, together
 * with the usage counts of the page.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import { useAppToast } from '@/core/composables/useAppToast'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'

import { useResourceUsage } from './useResourceUsage'

export function useResourceActions() {
  const { t } = useI18n()
  const toast = useAppToast()
  const confirm = useConfirm()
  const resources = useCookbookResources()
  const usage = useResourceUsage()
  const saving = ref(false)

  const reloadAll = () => Promise.all([resources.reload(), usage.reload()])

  async function save(action: () => Promise<unknown>): Promise<boolean> {
    saving.value = true
    try {
      await action()
      await reloadAll()
      toast.success(t('common.saved'))
      return true
    } catch (err) {
      toast.error(err)
      return false
    } finally {
      saving.value = false
    }
  }

  function remove(message: string, action: () => Promise<unknown>) {
    confirm.require({
      message,
      header: t('common.confirm'),
      acceptProps: { label: t('common.delete'), severity: 'danger' },
      rejectProps: { label: t('common.cancel'), text: true },
      accept: () => {
        void (async () => {
          try {
            await action()
            await reloadAll()
            toast.success(t('common.done'))
          } catch (err) {
            toast.error(err)
          }
        })()
      },
    })
  }

  /**
   * Runs a change that needs no confirmation toast, such as a new order
   * after a drag, and reloads the shared cache once afterwards, also when the
   * change failed halfway, so the table shows what the server holds.
   */
  async function apply(action: () => Promise<unknown>): Promise<boolean> {
    let ok = true
    try {
      await action()
    } catch (err) {
      toast.error(err)
      ok = false
    }
    try {
      await reloadAll()
    } catch (err) {
      if (ok) toast.error(err)
      ok = false
    }
    return ok
  }

  /** Reloads the shared cache after a dialog changed something. */
  function refresh() {
    reloadAll().catch((err: unknown) => toast.error(err))
  }

  return { resources, usage, saving, save, remove, apply, refresh }
}
