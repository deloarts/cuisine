import { describe, expect, it } from 'vitest'

import { addRecipient } from '@/features/admin-settings/mailRecipients'

describe('addRecipient', () => {
  it('adds a trimmed address once', () => {
    expect(addRecipient([], ' admin@example.org ')).toEqual({ recipients: ['admin@example.org'], error: null })
    expect(addRecipient(['admin@example.org'], 'Admin@Example.org').recipients).toEqual(['admin@example.org'])
  })

  it('refuses something that is not an address and ignores empty input', () => {
    expect(addRecipient(['a@b.at'], 'not an address')).toEqual({ recipients: ['a@b.at'], error: 'invalid' })
    expect(addRecipient(['a@b.at'], '   ')).toEqual({ recipients: ['a@b.at'], error: null })
  })
})
