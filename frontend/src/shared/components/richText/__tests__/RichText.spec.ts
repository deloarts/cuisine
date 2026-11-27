import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import RichText from '@/shared/components/richText/RichText.vue'

const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] })

describe('RichText', () => {
  it('highlights mentions unless the reader asked for plain ones', () => {
    const highlighted = mount(RichText, { props: { text: 'Cut the onion.' }, global: { plugins: [router] } })
    expect(highlighted.get('.rich-text').classes()).not.toContain('rich-text--plain-mentions')

    const plain = mount(RichText, {
      props: { text: 'Cut the onion.', plainMentions: true },
      global: { plugins: [router] },
    })
    expect(plain.get('.rich-text').classes()).toContain('rich-text--plain-mentions')
  })
})
