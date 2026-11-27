/**
 * A settings form that renders all of its fields at once and fills them when
 * the stored values arrive. Until then the form holds a blank: switches off,
 * texts, numbers and choices empty, and `loaded` stays false so the section
 * can keep its controls and its save button disabled. Nothing in the blank
 * pretends to be a stored value.
 */
import { onMounted, ref, type Ref } from 'vue'

import { useAppToast } from '@/core/composables/useAppToast'

/** The form before the values arrive: every text, number and choice may be empty. */
export type Draft<T> = {
  [K in keyof T]: T[K] extends boolean ? T[K] : T[K] extends object ? T[K] : T[K] | null
}

export function useSettingsForm<T extends object>(blank: Draft<T>, fetch: () => Promise<T>, enabled = true) {
  const toast = useAppToast()
  const form = ref(blank) as Ref<Draft<T>>
  const loaded = ref(false)

  /** Puts stored values into the form, after loading and after a save. */
  function adopt(value: T) {
    form.value = value as Draft<T>
    loaded.value = true
  }

  async function load() {
    try {
      adopt(await fetch())
    } catch (err) {
      toast.error(err)
    }
  }

  /** The form as the API takes it; only called once the form is loaded. */
  function value(): T {
    return form.value as T
  }

  onMounted(() => {
    if (enabled) void load()
  })

  return { form, loaded, adopt, load, value }
}
