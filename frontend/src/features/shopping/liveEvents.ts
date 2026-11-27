/**
 * The live connection of one shopping list. The backend streams server-sent
 * events: `ready` once connected, then `change` whenever someone edits the
 * list. Each event only says what changed, so the page refetches the list;
 * a reconnect (the stream closes every 30 minutes, and networks drop) also
 * refetches, because changes may have been missed in between.
 */
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

export interface ListChange {
  type: 'items_changed' | 'list_changed' | 'list_deleted'
  list_id: string
  by: string | null
}

export type LiveAction = 'refetch' | 'deleted' | 'ignore'

/**
 * What the page does with one event. A `ready` after the first one means the
 * browser reconnected; a change made by the viewer themselves still refetches,
 * since another of their devices may have made it.
 */
export function actionFor(event: { type: string; data: string }, listId: string, seenReady: boolean): LiveAction {
  if (event.type === 'ready') return seenReady ? 'refetch' : 'ignore'
  if (event.type !== 'change') return 'ignore'
  let change: Partial<ListChange>
  try {
    change = JSON.parse(event.data) as Partial<ListChange>
  } catch {
    return 'refetch'
  }
  if (change.list_id && change.list_id !== listId) return 'ignore'
  return change.type === 'list_deleted' ? 'deleted' : 'refetch'
}

export function eventsUrl(listId: string): string {
  const root = import.meta.env.VITE_API_URL ?? ''
  return `${root}/api/v1/web/shopping-lists/${encodeURIComponent(listId)}/events`
}

/**
 * Keeps an EventSource open for the list in `listId` while the component
 * lives, calling `onRefetch` or `onDeleted` as events arrive. `connected`
 * tells the page whether it is live, for a small indicator.
 */
export function useShoppingListEvents(
  listId: Ref<string | null>,
  handlers: { onRefetch: () => void; onDeleted: () => void },
) {
  const connected = ref(false)
  let source: EventSource | null = null
  let seenReady = false

  function close() {
    source?.close()
    source = null
    connected.value = false
  }

  function open(id: string) {
    close()
    seenReady = false
    if (typeof EventSource === 'undefined') return
    source = new EventSource(eventsUrl(id), { withCredentials: true })
    const handle = (event: MessageEvent<string>) => {
      const action = actionFor({ type: event.type, data: event.data }, id, seenReady)
      if (event.type === 'ready') {
        seenReady = true
        connected.value = true
      }
      if (action === 'refetch') handlers.onRefetch()
      if (action === 'deleted') handlers.onDeleted()
    }
    source.addEventListener('ready', handle)
    source.addEventListener('change', handle)
    source.onerror = () => {
      connected.value = false
    }
  }

  watch(
    listId,
    (id) => {
      if (id) open(id)
      else close()
    },
    { immediate: true },
  )
  onBeforeUnmount(close)

  return { connected }
}
