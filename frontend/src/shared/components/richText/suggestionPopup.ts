/**
 * Renders the `@` suggestions as a floating list next to the cursor, for
 * Tiptap's suggestion plugin. The list is a Vue component mounted on the
 * document body and placed with floating-ui.
 */
import { computePosition, flip, offset, shift } from '@floating-ui/dom'
import { VueRenderer } from '@tiptap/vue-3'
import type { SuggestionOptions, SuggestionProps } from '@tiptap/suggestion'

import MentionList from '@/shared/components/richText/MentionList.vue'
import type { MentionRef } from '@/shared/components/richText/mentions'

type Props = SuggestionProps<MentionRef>

export const suggestionPopup: SuggestionOptions<MentionRef>['render'] = () => {
  let renderer: VueRenderer | null = null

  function place(props: Props) {
    const element = renderer?.element as HTMLElement | undefined
    const rect = props.clientRect?.()
    if (!element || !rect) return
    const anchor = { getBoundingClientRect: () => rect }
    void computePosition(anchor, element, {
      placement: 'bottom-start',
      strategy: 'fixed',
      middleware: [offset(6), flip(), shift({ padding: 8 })],
    }).then(({ x, y }) => {
      Object.assign(element.style, { position: 'fixed', left: `${x}px`, top: `${y}px`, zIndex: '1200' })
    })
  }

  return {
    onStart: (props: Props) => {
      renderer = new VueRenderer(MentionList, {
        props: { items: props.items, command: props.command },
        editor: props.editor,
      })
      if (renderer.element) document.body.appendChild(renderer.element)
      place(props)
    },
    onUpdate: (props: Props) => {
      renderer?.updateProps({ items: props.items, command: props.command })
      place(props)
    },
    onKeyDown: ({ event }) => {
      if (event.key === 'Escape') {
        renderer?.destroy()
        renderer?.element?.remove()
        renderer = null
        return true
      }
      const list = renderer?.ref as { onKeyDown?: (e: KeyboardEvent) => boolean } | undefined
      return list?.onKeyDown?.(event) ?? false
    },
    onExit: () => {
      renderer?.element?.remove()
      renderer?.destroy()
      renderer = null
    },
  }
}
