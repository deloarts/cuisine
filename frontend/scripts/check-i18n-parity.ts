/**
 * i18n key-parity gate.
 *
 * en-GB is the fallback locale (src/core/i18n/index.ts), so a key missing
 * there renders as a raw key path. A key missing in de-AT falls back to
 * English silently, so a German user meets an English string in the middle
 * of German copy. Both fail: every key exists in both locales, the core
 * file and every feature module (src/features/<feature>/locales) alike.
 * A feature module must not define a top-level namespace that the core file
 * or another module already defines, and every permission needs a label in
 * both languages.
 *
 * Run: npm run check:i18n
 */
import { existsSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

import { ALL_PERMISSIONS } from '../src/core/auth/permissions'
import deATCore from '../src/core/i18n/locales/de-AT'
import enGBCore from '../src/core/i18n/locales/en-GB'
import { mergeMessages, type Messages } from '../src/core/i18n/messages'

const featuresDir = join(import.meta.dirname, '../src/features')

function keys(messages: Messages, prefix = ''): string[] {
  return Object.entries(messages).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return value && typeof value === 'object' ? keys(value as Messages, path) : [path]
  })
}

async function loadModules(locale: 'en-GB' | 'de-AT'): Promise<Record<string, Messages>> {
  const modules: Record<string, Messages> = {}
  for (const feature of readdirSync(featuresDir).sort()) {
    const file = join(featuresDir, feature, 'locales', `${locale}.ts`)
    if (!existsSync(file)) continue
    const module = (await import(file)) as { default: Messages }
    modules[feature] = module.default
  }
  return modules
}

const problems: string[] = []

const enModules = await loadModules('en-GB')
const deModules = await loadModules('de-AT')
for (const feature of new Set([...Object.keys(enModules), ...Object.keys(deModules)])) {
  if (!enModules[feature]) problems.push(`features/${feature}/locales/en-GB.ts is missing`)
  if (!deModules[feature]) problems.push(`features/${feature}/locales/de-AT.ts is missing`)
}

const enMerged = mergeMessages(enGBCore, enModules)
const deMerged = mergeMessages(deATCore, deModules)
problems.push(
  ...new Set(
    [...enMerged.collisions, ...deMerged.collisions].map((c) => `namespace defined twice: ${c}`),
  ),
)

const en = new Set(keys(enMerged.messages))
const de = new Set(keys(deMerged.messages))
problems.push(
  ...[...en].filter((k) => !de.has(k)).map((k) => `de-AT is missing ${k}`),
  ...[...de].filter((k) => !en.has(k)).map((k) => `en-GB is missing ${k}`),
  ...ALL_PERMISSIONS.map((p) => `permissions.${p.replace(':', '_')}`)
    .filter((k) => !en.has(k) || !de.has(k))
    .map((k) => `no label for ${k}`),
)

if (problems.length) {
  console.error(problems.join('\n'))
  process.exit(1)
}
console.log(
  `i18n parity OK (${en.size} keys, ${Object.keys(enModules).length} feature modules).`,
)
