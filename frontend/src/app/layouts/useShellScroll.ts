import { nextTick, onBeforeUnmount, onMounted, type Ref } from 'vue'
import { useRouter } from 'vue-router'

/** How long a restored position waits for a page to load enough content. */
const RESTORE_MS = 1500

/**
 * Gives the shell's scroll area the scroll behaviour a browser gives the
 * window, which the router cannot do because the page scrolls inside
 * `<main>`: a new page opens at its top, and going back or forward returns
 * to where that page was left. A page that only changes its query (a
 * filter or a tab) keeps its position. A restored page usually loads its
 * content after it renders, so the position is retried for a moment until
 * the content is tall enough to reach it.
 */
export function useShellScroll(main: Ref<HTMLElement | null>): void {
  const router = useRouter()
  const positions = new Map<string, number>()
  let popped = false
  let frame = 0

  function onPop() {
    popped = true
  }

  function restore(el: HTMLElement, top: number, until: number) {
    el.scrollTop = top
    if (el.scrollTop >= top - 1 || performance.now() > until) return
    frame = requestAnimationFrame(() => restore(el, top, until))
  }

  const removeBefore = router.beforeEach((_to, from) => {
    if (main.value) positions.set(from.fullPath, main.value.scrollTop)
  })
  const removeAfter = router.afterEach((to, from, failure) => {
    const back = popped
    popped = false
    if (failure || to.path === from.path) return
    cancelAnimationFrame(frame)
    void nextTick(() => {
      const el = main.value
      if (!el) return
      const top = back ? (positions.get(to.fullPath) ?? 0) : 0
      restore(el, top, performance.now() + RESTORE_MS)
    })
  })

  onMounted(() => window.addEventListener('popstate', onPop))
  onBeforeUnmount(() => {
    window.removeEventListener('popstate', onPop)
    cancelAnimationFrame(frame)
    removeBefore()
    removeAfter()
  })
}
