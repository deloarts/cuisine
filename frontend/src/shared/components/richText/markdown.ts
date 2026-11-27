/**
 * Recipe text (descriptions, tips, step texts) is a small Markdown subset:
 * bold, italic, bullet lists, numbered lists, paragraphs and line breaks.
 * The editor writes it and the renderer shows it; both use the rules here,
 * so a mark the editor cannot make is never rendered either.
 *
 * Text written before the editor existed is plain text whose single line
 * breaks matter; the renderer keeps them (`breaks: true`), so that text reads
 * exactly as it did.
 */
import MarkdownIt from 'markdown-it'
import { Markdown } from '@tiptap/markdown'
import StarterKit from '@tiptap/starter-kit'
import type { Extensions } from '@tiptap/core'

import {
  isMentionRef,
  matchMention,
  mentionExtension,
  type MentionRef,
  type MentionSource,
} from '@/shared/components/richText/mentions'

/**
 * How a mention reads where it is shown: its current name, in cook mode the
 * scaled amount, and for an accessible sub-recipe the recipe to link to.
 * Without an answer the stored name shows.
 */
export interface MentionDisplay {
  name: string
  amount?: string
  recipeId?: string | null
}
export type MentionResolver = (ref: MentionRef) => MentionDisplay | null

// html: false escapes every tag, so stored text can never inject markup.
const renderer = new MarkdownIt('zero', { html: false, linkify: false, breaks: true })
  .enable(['paragraph', 'list', 'newline', 'escape', 'emphasis', 'text'])

renderer.inline.ruler.before('emphasis', 'mention', (state, silent) => {
  if (state.src.charCodeAt(state.pos) !== 0x40) return false
  const m = matchMention(state.src.slice(state.pos))
  if (!m) return false
  if (!silent) state.push('mention', '', 0).meta = { ...m }
  state.pos += m.raw.length
  return true
})

renderer.renderer.rules.mention = (tokens, idx, _options, env: unknown) => {
  const ref: unknown = tokens[idx]!.meta
  if (!isMentionRef(ref)) return ''
  const resolve = (env as { resolve?: MentionResolver } | undefined)?.resolve
  const shown = resolve?.(ref) ?? null
  const esc = renderer.utils.escapeHtml
  const name = esc(shown?.name ?? ref.name)
  const amount = shown?.amount ? `<strong>${esc(shown.amount)}</strong> ` : ''
  if (ref.kind === 'recipe' && shown?.recipeId) {
    const id = esc(shown.recipeId)
    return `<a class="mention mention--recipe" href="/recipes/${id}" data-recipe-id="${id}">${amount}${name}</a>`
  }
  return `<span class="mention mention--${ref.kind}">${amount}${name}</span>`
}

/** The subset as safe HTML, for v-html, with mentions resolved by `resolve`. */
export function renderMarkdown(text: string | null | undefined, resolve?: MentionResolver): string {
  if (!text) return ''
  return renderer.render(text, { resolve })
}

/**
 * Prepares stored text for the editor. A single line break in plain text is
 * a visible break, while Markdown would join the lines, so it becomes a hard
 * break ("\" at the line end); list items and paragraph gaps are left alone.
 */
export function toEditorMarkdown(text: string | null | undefined): string {
  if (!text) return ''
  const lines = text.replace(/\r\n?/g, '\n').split('\n')
  const isList = (line: string) => /^\s*([-*+]|\d+[.)])\s/.test(line)
  return lines
    .map((line, i) => {
      const next = lines[i + 1]
      const breaks =
        next !== undefined &&
        line.trim() !== '' &&
        next.trim() !== '' &&
        !isList(line) &&
        !isList(next) &&
        !line.endsWith('\\') &&
        !line.endsWith('  ')
      return breaks ? `${line}\\` : line
    })
    .join('\n')
}

/**
 * The editor's schema: exactly the subset, nothing StarterKit adds beyond
 * it. Step text adds mentions; `mentions` then says where `@` suggestions
 * come from (null keeps existing chips without offering new ones).
 */
export function richTextExtensions(options: { mentions?: MentionSource | null } = {}): Extensions {
  const extras = 'mentions' in options ? [mentionExtension(options.mentions ?? null)] : []
  return [
    StarterKit.configure({
      heading: false,
      blockquote: false,
      codeBlock: false,
      code: false,
      horizontalRule: false,
      strike: false,
      link: false,
      underline: false,
    }),
    Markdown,
    ...extras,
  ]
}
