import { watch } from 'vue'
import { createI18n } from 'vue-i18n'

import enGBCore from './locales/en-GB'
import deATCore from './locales/de-AT'
import { featureOf, mergeMessages, type Messages } from './messages'

export type AppLocale = 'enGB' | 'deAT'

// Every feature's locale modules, loaded with the bundle so no string ever
// arrives after its page has rendered.
const enGBModules = import.meta.glob<Messages>('../../features/*/locales/en-GB.ts', {
  eager: true,
  import: 'default',
})
const deATModules = import.meta.glob<Messages>('../../features/*/locales/de-AT.ts', {
  eager: true,
  import: 'default',
})

// The merged messages keep the core file's type: vue-i18n infers its message
// schema from it, and the feature keys are looked up by string like any other.
type CoreMessages = typeof enGBCore

function assemble(core: Messages, modules: Record<string, Messages>): CoreMessages {
  const byFeature = Object.fromEntries(
    Object.entries(modules).map(([path, module]) => [featureOf(path), module]),
  )
  const { messages, collisions } = mergeMessages(core, byFeature)
  // npm run check:i18n fails on a collision; this only makes it visible
  // while developing.
  if (collisions.length && import.meta.env.DEV) {
    console.warn(`i18n namespaces defined twice: ${collisions.join(', ')}`)
  }
  return messages as CoreMessages
}

export const i18n = createI18n({
  legacy: false,
  locale: 'enGB',
  fallbackLocale: 'enGB',
  messages: {
    enGB: assemble(enGBCore, enGBModules),
    deAT: assemble(deATCore, deATModules),
  },
})

// Keeps <html lang> aligned with the active UI language; screen readers and
// the browser's spellcheck and translation prompts key off this attribute.
watch(
  i18n.global.locale,
  (locale) => {
    document.documentElement.lang = locale === 'deAT' ? 'de-AT' : 'en-GB'
  },
  { immediate: true },
)
