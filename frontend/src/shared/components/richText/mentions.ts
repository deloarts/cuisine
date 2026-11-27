/**
 * Mentions in step text. A mention is stored in the Markdown subset as
 * `@[Name](ingredient:<id>)`, `@[Name](recipe:<id>)` or
 * `@[Name](equipment:<id>)` and always points at one of the step's own lines
 * or equipment items; the backend refuses anything else.
 * The editor shows it as a chip and the renderer as a highlighted name,
 * taking the current name from the step's lines rather than the stored one.
 */
import Mention from '@tiptap/extension-mention'
import type { SuggestionOptions } from '@tiptap/suggestion'

export type MentionKind = 'ingredient' | 'recipe' | 'equipment'

export const MENTION_KINDS: readonly MentionKind[] = ['ingredient', 'recipe', 'equipment']

export interface MentionRef {
  kind: MentionKind
  id: string
  name: string
  /** The other name a suggestion matched, shown as "Tomate → Paradeiser"; never stored. */
  alias?: string | null
}

/** Whether a value carries a mention's kind, id and name, for the untyped hand-offs of markdown-it and tiptap. */
export function isMentionRef(value: unknown): value is MentionRef {
  if (typeof value !== 'object' || value === null) return false
  const { kind, id, name } = value as Record<string, unknown>
  return MENTION_KINDS.includes(kind as MentionKind) && typeof id === 'string' && typeof name === 'string'
}

const TOKEN_SOURCE = String.raw`@\[([^\]\n]+)\]\((ingredient|recipe|equipment):([0-9A-Fa-f-]{36})\)`
const TOKEN = new RegExp(`^${TOKEN_SOURCE}`)

/** Every mention in a text, in order. */
export function parseMentions(text: string | null | undefined): MentionRef[] {
  if (!text) return []
  return [...text.matchAll(new RegExp(TOKEN_SOURCE, 'g'))].map((m) => ({
    name: m[1]!,
    kind: m[2] as MentionKind,
    id: m[3]!,
  }))
}

/** Matches a mention at the very start of `src`, for the Markdown tokenizers. */
export function matchMention(src: string): (MentionRef & { raw: string }) | null {
  const m = TOKEN.exec(src)
  return m ? { raw: m[0], name: m[1]!, kind: m[2] as MentionKind, id: m[3]! } : null
}

/** The stored token. Brackets and line breaks in a name cannot be stored, so they go. */
export function mentionToken(ref: MentionRef): string {
  const name = ref.name.replace(/[[\]\n\r]+/g, ' ').replace(/\s+/g, ' ').trim() || '?'
  return `@[${name}](${ref.kind}:${ref.id})`
}

/** Turns the mentions of one line or item back into plain names, for when it goes. */
export function unlinkMentions(text: string, kind: MentionKind, id: string): string {
  return text.replace(new RegExp(TOKEN_SOURCE, 'g'), (whole, name: string, k: string, i: string) =>
    k === kind && i.toLowerCase() === id.toLowerCase() ? name : whole,
  )
}

/** The Mention node keeps kind and id together in its `id` attribute. */
export function splitMentionId(value: string): { kind: MentionKind; id: string } | null {
  const [kind, id] = value.split(':')
  return (MENTION_KINDS as readonly string[]).includes(kind ?? '') && id
    ? { kind: kind as MentionKind, id }
    : null
}

/** What the editor's `@` suggestions offer and what picking one does. */
export interface MentionSource {
  search: (query: string) => Promise<MentionRef[]>
  /** Called after a chip was inserted, e.g. to add the step line it names. */
  picked?: (ref: MentionRef) => void
  /** The popup; the editor supplies its own. */
  render?: SuggestionOptions<MentionRef>['render']
}

/** The Mention node with the token as its Markdown form. */
export function mentionExtension(source: MentionSource | null) {
  return Mention.extend({
    markdownTokenName: 'mention',
    markdownTokenizer: {
      name: 'mention',
      level: 'inline',
      start: (src: string) => src.indexOf('@['),
      tokenize: (src: string) => {
        const m = matchMention(src)
        return m ? { type: 'mention', raw: m.raw, name: m.name, kind: m.kind, id: m.id } : undefined
      },
    },
    parseMarkdown: (token) => ({
      type: 'mention',
      attrs: { id: `${String(token.kind)}:${String(token.id)}`, label: String(token.name) },
    }),
    renderMarkdown: (node) => {
      const parts = splitMentionId(String(node.attrs?.id ?? ''))
      const name = String(node.attrs?.label ?? '')
      return parts ? mentionToken({ ...parts, name }) : name
    },
  }).configure({
    HTMLAttributes: { class: 'mention-chip' },
    renderText: ({ node }) => String(node.attrs.label ?? ''),
    renderHTML: ({ options, node }) => [
      'span',
      {
        ...options.HTMLAttributes,
        'data-kind': splitMentionId(String(node.attrs.id ?? ''))?.kind ?? 'ingredient',
      },
      String(node.attrs.label ?? ''),
    ],
    suggestion: {
      char: '@',
      allowSpaces: true,
      items: async ({ query }) => (source ? await source.search(query) : []),
      // The suggestion items are MentionRefs, not the node's own attributes.
      command: ({ editor, range, props }) => {
        const ref: unknown = props
        if (!isMentionRef(ref)) return
        editor
          .chain()
          .focus()
          .insertContentAt(range, [
            { type: 'mention', attrs: { id: `${ref.kind}:${ref.id}`, label: ref.name } },
            { type: 'text', text: ' ' },
          ])
          .run()
        source?.picked?.(ref)
      },
      render: source?.render as never,
    },
  })
}
