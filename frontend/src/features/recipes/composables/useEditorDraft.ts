/**
 * Keeps an editor's unsaved form on the device while the user works, and
 * brings it back when they return to the same editor. The form is compared
 * with the server's version it was loaded from: only a form that differs is
 * stored, and a stored draft equal to the server's version is dropped.
 *
 * The view calls `start` once the server's version is in the form, `clear`
 * after a successful save or a confirmed cancel (`confirmLeave` asks while
 * the form has unsaved changes), and `discard` to go back to the server's
 * version. Writes are debounced and flushed when the editor
 * unmounts or the page is hidden, so closing the tab right after typing keeps
 * the last change. `upgrade` brings a draft stored by an earlier release
 * into the form's current shape before it is compared or restored.
 *
 * An image is uploaded as soon as it is picked, and the server deletes an
 * upload that nothing has used for 30 days. With `images`, a restored draft
 * asks the server for each image the draft added (the saved version's own
 * images are in use and stay) and removes those that are gone from the form,
 * so saving an old draft does not fail; the notice then says so.
 */
import { useEventListener } from '@vueuse/core'
import { useConfirm } from 'openvue/useconfirm'
import { computed, onBeforeUnmount, ref, watch, type WatchStopHandle } from 'vue'
import { useI18n } from 'vue-i18n'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { editorDrafts } from '@/core/utils/editorDrafts'
import { errorStatus } from '@/core/utils/errors'
import { getFile } from '@/features/recipes/api/editorSupport'
import { nextKey } from '@/features/recipes/composables/recipeEditorState'

const WRITE_DELAY_MS = 500

export interface RestoredDraft {
  savedAt: string
  // The server's version changed after the draft was stored.
  serverChanged: boolean
  // How many of the draft's images were gone from the server and removed.
  droppedImages: number
}

/** Where a form keeps its image ids, for checking a restored draft's images. */
export interface DraftImages<T> {
  ids: (form: T) => (string | null | undefined)[]
  /** Removes the given ids from the form. */
  drop: (form: T, missing: Set<string>) => void
}

// Of the ids, those the server no longer has. Any other answer than a 404
// keeps the image, so a network hiccup never removes one.
async function missingFiles(ids: string[]): Promise<Set<string>> {
  const answers = await Promise.all(
    ids.map(async (id) => {
      try {
        await getFile(id)
        return null
      } catch (err) {
        return errorStatus(err) === 404 ? id : null
      }
    }),
  )
  return new Set(answers.filter((id): id is string => id !== null))
}

// The form without its v-for keys, which are fresh on every load and say
// nothing about the content.
function comparable(value: unknown): string {
  return JSON.stringify(value, (k, v: unknown) => (k === 'key' ? undefined : v))
}

// A restored form gets new v-for keys, so they cannot collide with keys the
// editor hands out from now on.
function rekey<T>(value: T): T {
  if (Array.isArray(value)) return value.map(rekey) as T
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k, k === 'key' && typeof v === 'string' ? nextKey() : rekey(v)]),
    ) as T
  }
  return value
}

export function useEditorDraft<T extends object>(
  form: T,
  scope: () => string,
  upgrade: (stored: T) => T = (stored) => stored,
  images?: DraftImages<T>,
) {
  const currentUser = useCurrentUserStore()
  const confirm = useConfirm()
  const { t } = useI18n()
  const restored = ref<RestoredDraft | null>(null)
  const pristine = ref<string | null>(null)
  let snapshot: string | null = null
  let base: string | null = null
  // The scope as it was at `start`: by the time the editor unmounts, the
  // route already points at the next page.
  let key: string | null = null
  let stopWatch: WatchStopHandle | null = null
  let timer: ReturnType<typeof setTimeout> | null = null

  /** Whether the form differs from the server's version it was loaded from. */
  const dirty = computed(() => pristine.value !== null && comparable(form) !== pristine.value)

  function userId(): string | null {
    return currentUser.user?.id ?? null
  }

  function persist() {
    timer = null
    const user = userId()
    if (!user || key === null || pristine.value === null) return
    if (comparable(form) === pristine.value) editorDrafts.remove(user, key)
    else editorDrafts.write(user, key, base, form)
  }

  function flush() {
    if (timer === null) return
    clearTimeout(timer)
    persist()
  }

  function cancelPending() {
    if (timer !== null) clearTimeout(timer)
    timer = null
  }

  /**
   * Takes the form as it is now as the server's version, restores a stored
   * draft that differs from it and keeps storing changes from here on.
   * `serverBase` is the record's `changed` timestamp, or null for a new one.
   */
  function start(serverBase: string | null | undefined) {
    stopWatch?.()
    cancelPending()
    base = serverBase ?? null
    key = scope()
    pristine.value = comparable(form)
    snapshot = JSON.stringify(form)
    restored.value = null
    const user = userId()
    const stored = user ? editorDrafts.read<T>(user, key) : null
    if (user && stored) {
      const data = upgrade(stored.data)
      if (comparable(data) !== pristine.value) {
        Object.assign(form, rekey(data))
        restored.value = {
          savedAt: stored.savedAt,
          serverChanged: base !== null && stored.base !== null && stored.base !== base,
          droppedImages: 0,
        }
        if (images) void dropMissingImages(images, JSON.parse(snapshot) as T)
      } else {
        editorDrafts.remove(user, key)
      }
    }
    stopWatch = watch(
      () => comparable(form),
      () => {
        cancelPending()
        timer = setTimeout(persist, WRITE_DELAY_MS)
      },
    )
  }

  async function dropMissingImages(images: DraftImages<T>, server: T) {
    const known = new Set(images.ids(server).filter(Boolean))
    const added = [...new Set(images.ids(form).filter((id): id is string => !!id && !known.has(id)))]
    if (!added.length) return
    const startedFor = key
    const missing = await missingFiles(added)
    // The editor may have moved on to another record or been reset meanwhile.
    if (!missing.size || key !== startedFor || !restored.value) return
    images.drop(form, missing)
    restored.value = { ...restored.value, droppedImages: missing.size }
  }

  /** Drops the stored draft and stops storing, after a save or a cancel. */
  function clear() {
    stopWatch?.()
    stopWatch = null
    cancelPending()
    const user = userId()
    if (user && key !== null) editorDrafts.remove(user, key)
    key = null
    pristine.value = null
    restored.value = null
  }

  /** Drops the stored draft and puts the server's version back into the form. */
  function discard() {
    cancelPending()
    const user = userId()
    if (user && key !== null) editorDrafts.remove(user, key)
    if (snapshot !== null) Object.assign(form, rekey(JSON.parse(snapshot) as T))
    restored.value = null
  }

  /** Whether the user may leave: at once without changes, else after confirming. */
  function confirmLeave(): Promise<boolean> {
    if (!dirty.value) return Promise.resolve(true)
    return new Promise((resolve) => {
      confirm.require({
        header: t('recipes.editorDraft.confirmTitle'),
        message: t('recipes.editorDraft.confirm'),
        acceptProps: { label: t('recipes.editorDraft.confirmAccept'), severity: 'danger' },
        rejectProps: { label: t('recipes.editorDraft.keepEditing'), text: true },
        accept: () => resolve(true),
        reject: () => resolve(false),
        onHide: () => resolve(false),
      })
    })
  }

  useEventListener(window, 'pagehide', flush)
  onBeforeUnmount(() => {
    flush()
    stopWatch?.()
  })

  return { restored, dirty, start, clear, discard, flush, confirmLeave }
}
