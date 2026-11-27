import { Editor } from '@tiptap/core'
import { afterEach, describe, expect, it } from 'vitest'

import {
  renderMarkdown,
  richTextExtensions,
  toEditorMarkdown,
} from '@/shared/components/richText/markdown'

let editor: Editor | null = null

function roundTrip(text: string): string {
  editor = new Editor({
    extensions: richTextExtensions(),
    content: toEditorMarkdown(text),
    contentType: 'markdown',
  })
  return editor.getMarkdown()
}

afterEach(() => {
  editor?.destroy()
  editor = null
})

describe('editor round trip', () => {
  it.each([
    'Brown the **onions** in *hot* fat.',
    '- one\n- two',
    '1. one\n2. two',
    'First paragraph.\n\nSecond paragraph.',
    'Mix:\n\n- **flour**\n- *a pinch* of salt\n\nThen rest.',
  ])('keeps %j as it is', (text) => {
    expect(roundTrip(text)).toBe(text)
  })

  it('keeps the line breaks of old plain text as hard breaks', () => {
    const saved = roundTrip('Line one\nLine two')
    expect(saved).toBe('Line one  \nLine two')
    expect(renderMarkdown(saved)).toBe(renderMarkdown('Line one\nLine two'))
  })

  it('drops what the subset has no room for', () => {
    expect(roundTrip('# Title')).not.toContain('#')
    expect(roundTrip('[site](https://example.com)')).not.toContain('](')
  })
})

describe('toEditorMarkdown', () => {
  it('marks single line breaks and leaves lists and paragraphs alone', () => {
    expect(toEditorMarkdown('a\nb\n\nc')).toBe('a\\\nb\n\nc')
    expect(toEditorMarkdown('- a\n- b')).toBe('- a\n- b')
    expect(toEditorMarkdown('a  \nb')).toBe('a  \nb')
  })
})

describe('renderMarkdown', () => {
  it('renders bold, italic and both kinds of list', () => {
    const html = renderMarkdown('**a** *b*\n\n- c\n\n1. d')
    expect(html).toContain('<strong>a</strong> <em>b</em>')
    expect(html).toContain('<ul>\n<li>c</li>')
    expect(html).toContain('<ol>\n<li>d</li>')
  })

  it('renders old plain text with its line breaks unchanged', () => {
    expect(renderMarkdown('Cut the onions.\nFry them.')).toBe('<p>Cut the onions.<br>\nFry them.</p>\n')
  })

  it('never executes HTML from the text', () => {
    const html = renderMarkdown('<script>alert(1)</script><img src=x onerror="alert(1)">')
    expect(html).not.toContain('<script')
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;script&gt;')
  })

  it('leaves headings, links, images and code as plain text', () => {
    const html = renderMarkdown('# T\n\n[x](javascript:alert(1)) ![i](x.png) `c`')
    expect(html).not.toMatch(/<h1|<a |<img|<code/)
    expect(html).toContain('# T')
  })

  it('is empty for no text', () => {
    expect(renderMarkdown(null)).toBe('')
    expect(renderMarkdown('')).toBe('')
  })
})
