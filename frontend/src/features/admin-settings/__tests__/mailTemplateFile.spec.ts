import { describe, expect, it } from 'vitest'

import {
  insertAtCaret,
  isImportable,
  mailTemplateFileName,
  mailTemplateFileTarget,
  parseMailTemplateFile,
  planMailTemplateImport,
  serializeMailTemplateFile,
} from '@/features/admin-settings/mailTemplateFile'

const DOCUMENT = `<!DOCTYPE html>
<html lang="en">
<head>
  <title>Test from {{ instance_name }}</title>
</head>
<body><p>Hi</p></body>
</html>
`

describe('mail template file names', () => {
  it('reads kind and locale from the file name', () => {
    expect(mailTemplateFileTarget('test_mail.en-GB.html')).toEqual({ kind: 'test_mail', locale: 'en-GB' })
    expect(mailTemplateFileTarget('operational_alert.de-AT.htm')).toEqual({ kind: 'operational_alert', locale: 'de-AT' })
    expect(mailTemplateFileTarget('test_mail.html')).toBeNull()
    expect(mailTemplateFileTarget('test_mail (1).en-GB.html')).toBeNull()
  })

  it('writes the name the import reads back', () => {
    expect(mailTemplateFileTarget(mailTemplateFileName('test_mail', 'de-AT'))).toEqual({ kind: 'test_mail', locale: 'de-AT' })
  })
})

describe('parseMailTemplateFile', () => {
  it('takes the subject from the title and keeps a full document whole', () => {
    expect(parseMailTemplateFile(DOCUMENT)).toEqual({ subject: 'Test from {{ instance_name }}', body: DOCUMENT })
  })

  it('takes the leading title line out of a fragment', () => {
    const text = '<title>Alert &amp; more</title>\n<p>Details</p>\n'
    expect(parseMailTemplateFile(text)).toEqual({ subject: 'Alert & more', body: '<p>Details</p>\n' })
  })
})

describe('serializeMailTemplateFile', () => {
  it('writes the subject into the title of a full document', () => {
    const text = serializeMailTemplateFile({ subject: 'Hello <you>', body: DOCUMENT })
    expect(text).toContain('<title>Hello &lt;you&gt;</title>')
    expect(parseMailTemplateFile(text).subject).toBe('Hello <you>')
  })

  it('round-trips a fragment', () => {
    const content = { subject: 'Alert {{ title }}', body: '<p>Details</p>\n' }
    expect(parseMailTemplateFile(serializeMailTemplateFile(content))).toEqual(content)
  })

  it('adds a title to a document head without one', () => {
    const body = '<html><head><meta charset="UTF-8"></head><body></body></html>'
    const content = parseMailTemplateFile(serializeMailTemplateFile({ subject: 'Hi', body }))
    expect(content.subject).toBe('Hi')
    expect(content.body).toContain('<head>\n  <title>Hi</title>')
  })
})

describe('planMailTemplateImport', () => {
  const kinds = ['test_mail', 'operational_alert']
  const locales = ['en-GB', 'de-AT']
  const customized = new Set(['test_mail.en-GB'])

  function plan(names: string[], text = (name: string) => `<title>${name}</title>\n<p></p>`) {
    return planMailTemplateImport(
      names.map((name) => ({ name, text: text(name) })),
      kinds,
      locales,
      (kind, locale) => customized.has(`${kind}.${locale}`),
    )
  }

  it('tells new from replacing and unusable files', () => {
    const rows = plan([
      'test_mail.en-GB.html',
      'test_mail.de-AT.html',
      'welcome.en-GB.html',
      'test_mail.fr-FR.html',
      'readme.html',
    ])
    expect(rows.map((r) => r.status)).toEqual(['replaces', 'new', 'unknownKind', 'unknownLocale', 'badName'])
    expect(rows.filter(isImportable).map((r) => r.fileName)).toEqual(['test_mail.en-GB.html', 'test_mail.de-AT.html'])
  })

  it('refuses a file without a subject, which the backend would refuse too', () => {
    expect(plan(['test_mail.de-AT.html'], () => '<p>No title</p>')[0]?.status).toBe('noSubject')
  })

  it('lets the last file of a pair picked twice count', () => {
    const rows = plan(['test_mail.de-AT.html', 'test_mail.de-AT.htm'])
    expect(rows.map((r) => r.status)).toEqual(['duplicate', 'new'])
  })
})

describe('insertAtCaret', () => {
  it('inserts at the caret or over the selection', () => {
    expect(insertAtCaret('Hello !', 6, 6, 'you')).toEqual({ value: 'Hello you!', caret: 9 })
    expect(insertAtCaret('Hello there', 6, 11, '{{ name }}')).toEqual({ value: 'Hello {{ name }}', caret: 16 })
  })

  it('clamps a caret outside the text', () => {
    expect(insertAtCaret('ab', 10, 12, 'c')).toEqual({ value: 'abc', caret: 3 })
  })
})
