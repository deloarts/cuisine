import { describe, expect, it } from 'vitest'

import { renderLegalMarkdown } from '@/shared/components/legal/legalMarkdown'

describe('renderLegalMarkdown', () => {
  it('renders headings and lists', () => {
    const html = renderLegalMarkdown('## Who we are\n\n- one\n- two')
    expect(html).toContain('<h2>Who we are</h2>')
    expect(html).toContain('<li>one</li>')
  })

  it('escapes HTML and opens links in a new tab', () => {
    const html = renderLegalMarkdown('<script>x</script> [site](https://example.org)')
    expect(html).not.toContain('<script>')
    expect(html).toContain('target="_blank"')
    expect(html).toContain('rel="noopener noreferrer"')
  })

  it('renders nothing for no text', () => {
    expect(renderLegalMarkdown(null)).toBe('')
  })
})
