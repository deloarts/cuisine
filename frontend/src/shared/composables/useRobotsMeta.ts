/**
 * Sets the page's robots meta tag while a public page is shown and removes it
 * when the page goes: `index, follow` when the administrator lets search
 * engines index public recipes, `noindex, nofollow` otherwise. Every other
 * page sits behind the sign-in, which robots.txt closes anyway.
 */
import { onBeforeUnmount, watch, type Ref } from 'vue'

const NAME = 'robots'

function tag(): HTMLMetaElement {
  let meta = document.head.querySelector<HTMLMetaElement>(`meta[name="${NAME}"]`)
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = NAME
    document.head.appendChild(meta)
  }
  return meta
}

export function useRobotsMeta(indexable: Ref<boolean>): void {
  watch(
    indexable,
    (value) => {
      tag().content = value ? 'index, follow' : 'noindex, nofollow'
    },
    { immediate: true },
  )
  onBeforeUnmount(() => {
    document.head.querySelector(`meta[name="${NAME}"]`)?.remove()
  })
}
