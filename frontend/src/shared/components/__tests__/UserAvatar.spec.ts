import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import UserAvatar from '@/shared/components/UserAvatar.vue'

function initials(wrapper: ReturnType<typeof mount>): string | undefined {
  return wrapper.find('[data-initials]').attributes('data-initials')
}

describe('UserAvatar', () => {
  it('shows up to two initials without an avatar', () => {
    const wrapper = mount(UserAvatar, { props: { name: 'Anna Maria Huber' } })
    expect(wrapper.find('img').exists()).toBe(false)
    expect(initials(wrapper)).toBe('AM')
    // Decorative: the name stands next to it, so it adds no text.
    expect(wrapper.text()).toBe('')
  })

  it('shows a question mark for an empty name', () => {
    expect(initials(mount(UserAvatar, { props: { name: '' } }))).toBe('?')
  })

  it('shows the thumbnail of the avatar', () => {
    const wrapper = mount(UserAvatar, { props: { name: 'Anna', avatarId: 'abc' } })
    expect(wrapper.find('img').attributes('src')).toContain('/files/abc/content?variant=thumbnail')
  })

  it('prefers a given src, as the public pages pass their own route', () => {
    const wrapper = mount(UserAvatar, { props: { name: 'Anna', avatarId: 'abc', src: '/public/a.webp' } })
    expect(wrapper.find('img').attributes('src')).toBe('/public/a.webp')
  })

  it('falls back to the initials when the image fails, until the avatar changes', async () => {
    const wrapper = mount(UserAvatar, { props: { name: 'Anna', avatarId: 'abc' } })
    await wrapper.find('img').trigger('error')
    expect(wrapper.find('img').exists()).toBe(false)
    expect(initials(wrapper)).toBe('A')

    await wrapper.setProps({ avatarId: 'def' })
    expect(wrapper.find('img').attributes('src')).toContain('/files/def/')
  })
})
