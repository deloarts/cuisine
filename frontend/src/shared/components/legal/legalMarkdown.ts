/**
 * Legal pages (imprint, privacy statement) are written in plain Markdown with
 * headings, lists, emphasis and links, wider than the recipe subset. HTML in
 * the text is never rendered, and links open in a new tab without handing
 * over the page they came from.
 */
import MarkdownIt from 'markdown-it'

const renderer = new MarkdownIt('commonmark', { html: false, linkify: true }).enable('linkify')

const defaultLinkOpen =
  renderer.renderer.rules.link_open ??
  ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

renderer.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const token = tokens[idx]!
  token.attrSet('target', '_blank')
  token.attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen(tokens, idx, options, env, self)
}

export function renderLegalMarkdown(text: string | null | undefined): string {
  return text ? renderer.render(text) : ''
}
