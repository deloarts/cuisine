import { Editor } from '@tiptap/core'
import { afterEach, describe, expect, it } from 'vitest'

import { renderMarkdown, richTextExtensions } from '@/shared/components/richText/markdown'
import {
  mentionToken,
  parseMentions,
  unlinkMentions,
} from '@/shared/components/richText/mentions'

const FLOUR = '11111111-1111-4111-8111-111111111111'
const SHEETS = '22222222-2222-4222-8222-222222222222'

let editor: Editor | null = null

afterEach(() => {
  editor?.destroy()
  editor = null
})

function roundTrip(text: string): string {
  editor = new Editor({
    extensions: richTextExtensions({ mentions: null }),
    content: text,
    contentType: 'markdown',
  })
  return editor.getMarkdown()
}

describe('mention tokens', () => {
  it('round-trips ingredient and recipe mentions through the editor', () => {
    const text = `Mix @[Flour](ingredient:${FLOUR}) with **milk**, then layer @[Lasagna sheets](recipe:${SHEETS}).`
    expect(roundTrip(text)).toBe(text)
  })

  it('keeps mentions inside lists', () => {
    const text = `- @[Flour](ingredient:${FLOUR})\n- salt`
    expect(roundTrip(text)).toBe(text)
  })

  it('parses every mention with its kind and id', () => {
    expect(parseMentions(`a @[Flour](ingredient:${FLOUR}) b @[Sheets](recipe:${SHEETS})`)).toEqual([
      { name: 'Flour', kind: 'ingredient', id: FLOUR },
      { name: 'Sheets', kind: 'recipe', id: SHEETS },
    ])
    expect(parseMentions('@[x](ingredient:nope) and @someone')).toEqual([])
  })

  it('writes names that cannot break the token', () => {
    expect(mentionToken({ kind: 'ingredient', id: FLOUR, name: 'Odd ] name\n' })).toBe(
      `@[Odd name](ingredient:${FLOUR})`,
    )
  })

  it('turns the mentions of a removed line into plain names', () => {
    const text = `Add @[Flour](ingredient:${FLOUR}) and @[Sheets](recipe:${SHEETS}).`
    expect(unlinkMentions(text, 'ingredient', FLOUR)).toBe(`Add Flour and @[Sheets](recipe:${SHEETS}).`)
  })
})

describe('rendering mentions', () => {
  it('shows the current name and, in cook mode, the amount', () => {
    const html = renderMarkdown(`Sift @[Mehl](ingredient:${FLOUR}).`, (ref) =>
      ref.id === FLOUR ? { name: 'Flour', amount: '300 g' } : null,
    )
    expect(html).toContain('<span class="mention mention--ingredient"><strong>300 g</strong> Flour</span>')
  })

  it('links an accessible sub-recipe and keeps a hidden one as text', () => {
    const text = `Use @[Sheets](recipe:${SHEETS}).`
    expect(renderMarkdown(text, () => ({ name: 'Sheets', recipeId: SHEETS }))).toContain(
      `<a class="mention mention--recipe" href="/recipes/${SHEETS}" data-recipe-id="${SHEETS}">Sheets</a>`,
    )
    expect(renderMarkdown(text, () => ({ name: 'a recipe', recipeId: null }))).not.toContain('<a')
  })

  it('never lets a name inject HTML', () => {
    const stored = renderMarkdown(`@[<img src=x onerror=alert(1)>](ingredient:${FLOUR})`)
    expect(stored).not.toContain('<img')
    expect(stored).toContain('&lt;img')
    const resolved = renderMarkdown(`@[x](ingredient:${FLOUR})`, () => ({
      name: '<script>alert(1)</script>',
      amount: '<b>1</b>',
    }))
    expect(resolved).not.toMatch(/<script|<b>/)
  })
})

describe('equipment mentions', () => {
  const WHISK = '33333333-3333-4333-8333-333333333333'

  it('round-trips an equipment mention through the editor', () => {
    const text = `Beat with the @[Whisk](equipment:${WHISK}) until stiff.`
    expect(roundTrip(text)).toBe(text)
  })

  it('parses, unlinks and renders equipment like the other kinds', () => {
    const text = `Use @[Whisk](equipment:${WHISK}) and @[Flour](ingredient:${FLOUR}).`
    expect(parseMentions(text)).toEqual([
      { name: 'Whisk', kind: 'equipment', id: WHISK },
      { name: 'Flour', kind: 'ingredient', id: FLOUR },
    ])
    expect(unlinkMentions(text, 'equipment', WHISK)).toBe(`Use Whisk and @[Flour](ingredient:${FLOUR}).`)
    expect(renderMarkdown(text, (ref) => (ref.kind === 'equipment' ? { name: 'Balloon whisk' } : null))).toContain(
      '<span class="mention mention--equipment">Balloon whisk</span>',
    )
  })
})
