/**
 * The file format of a mail template, ported from Glados: one HTML file per
 * kind and language, named `<kind>.<locale>.html` (`test_mail.de-AT.html`),
 * whose `<title>` is the subject. A full document keeps its `<title>` in the
 * body, as the built-in templates do. A fragment has no head of its own, so
 * the export puts the subject in a leading `<title>` line and the import
 * takes that line out of the body again. The backend's export writes the
 * same names, so its files import again unchanged.
 */

const FILE_NAME = /^([a-z][a-z_]*)\.([a-z]{2}-[A-Z]{2})\.html?$/
const TITLE = /<title[^>]*>([\s\S]*?)<\/title>/i
const LEADING_TITLE = /^\s*<title[^>]*>[\s\S]*?<\/title>[^\S\n]*\n?/i
const FULL_DOCUMENT = /<(html|head)[\s>]/i
const HEAD_OPEN = /<head(\s[^>]*)?>/i

export interface MailTemplateFileTarget {
  kind: string
  locale: string
}

export interface MailTemplateFileContent {
  subject: string
  body: string
}

/** The kind and locale a file name stands for, or null for any other name. */
export function mailTemplateFileTarget(fileName: string): MailTemplateFileTarget | null {
  const match = FILE_NAME.exec(fileName)
  if (!match) return null
  return { kind: match[1]!, locale: match[2]! }
}

export function mailTemplateFileName(kind: string, locale: string): string {
  return `${kind}.${locale}.html`
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function unescapeHtml(text: string): string {
  return text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&')
}

export function parseMailTemplateFile(text: string): MailTemplateFileContent {
  const match = TITLE.exec(text)
  const subject = match ? unescapeHtml(match[1]!.trim()) : ''
  const body = FULL_DOCUMENT.test(text) ? text : text.replace(LEADING_TITLE, '')
  return { subject, body }
}

export function serializeMailTemplateFile({ subject, body }: MailTemplateFileContent): string {
  const title = `<title>${escapeHtml(subject)}</title>`
  if (TITLE.test(body)) return body.replace(TITLE, () => title)
  if (HEAD_OPEN.test(body)) return body.replace(HEAD_OPEN, (head) => `${head}\n  ${title}`)
  return `${title}\n${body}`
}

export type MailTemplateImportStatus = 'new' | 'replaces' | 'badName' | 'unknownKind' | 'unknownLocale' | 'noSubject' | 'duplicate'

export interface MailTemplateImportRow {
  fileName: string
  kind: string | null
  locale: string | null
  subject: string
  /** The file as picked, which the backend parses itself on import. */
  text: string
  status: MailTemplateImportStatus
}

/** Whether a row of an import plan is saved when the admin confirms it. */
export function isImportable(row: MailTemplateImportRow): boolean {
  return row.status === 'new' || row.status === 'replaces'
}

/**
 * What importing the picked files would do, one row per file. A file is
 * importable when its name names a known kind and locale and it has a
 * subject; it replaces the current template when that pair is customised
 * already. When a pair is picked twice, the last file counts and the earlier
 * ones are marked as duplicates.
 */
export function planMailTemplateImport(
  files: { name: string; text: string }[],
  kinds: readonly string[],
  locales: readonly string[],
  isCustomized: (kind: string, locale: string) => boolean,
): MailTemplateImportRow[] {
  const rows = files.map((file): MailTemplateImportRow => {
    const target = mailTemplateFileTarget(file.name)
    const { subject } = parseMailTemplateFile(file.text)
    const row = { fileName: file.name, subject, text: file.text }
    if (!target) return { ...row, kind: null, locale: null, status: 'badName' }
    const { kind, locale } = target
    let status: MailTemplateImportStatus
    if (!kinds.includes(kind)) status = 'unknownKind'
    else if (!locales.includes(locale)) status = 'unknownLocale'
    else if (!subject) status = 'noSubject'
    else status = isCustomized(kind, locale) ? 'replaces' : 'new'
    return { ...row, kind, locale, status }
  })
  const seen = new Set<string>()
  for (let i = rows.length - 1; i >= 0; i--) {
    const row = rows[i]!
    if (!isImportable(row)) continue
    const key = `${row.kind}.${row.locale}`
    if (seen.has(key)) row.status = 'duplicate'
    seen.add(key)
  }
  return rows
}

/** Inserts `text` at the textarea's caret (or over its selection) and returns the new value and caret. */
export function insertAtCaret(value: string, start: number, end: number, text: string): { value: string; caret: number } {
  const from = Math.max(0, Math.min(start, value.length))
  const to = Math.max(from, Math.min(end, value.length))
  return { value: value.slice(0, from) + text + value.slice(to), caret: from + text.length }
}
