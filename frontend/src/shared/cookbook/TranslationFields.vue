<script setup lang="ts">
/**
 * The text fields of a translatable record, once per content language. The
 * original language comes first and is required; the other languages are
 * optional, and an empty one falls back to the original when read. The
 * `locale` slot adds fields of the caller's own to each language's box, such
 * as that language's other names, so everything of one language sits together.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { CONTENT_LOCALES } from './contentLocale'
import type { ContentLocale } from './types'

export interface TranslationField {
  key: string
  label: string
}

const props = defineProps<{
  idPrefix: string
  fields: TranslationField[]
  originalLocale?: ContentLocale
  disabled?: boolean
}>()
const model = defineModel<Record<string, Record<string, string>>>({ required: true })
defineSlots<{ locale?: (props: { locale: ContentLocale }) => unknown }>()

const { t } = useI18n()

const locales = computed(() => {
  const original = props.originalLocale
  if (!original) return CONTENT_LOCALES
  return [original, ...CONTENT_LOCALES.filter((l) => l !== original)]
})

function value(locale: string, key: string): string {
  return model.value[locale]?.[key] ?? ''
}

function update(locale: string, key: string, text: string) {
  model.value = { ...model.value, [locale]: { ...model.value[locale], [key]: text } }
}
</script>

<template>
  <div class="translation-fields">
    <fieldset v-for="locale in locales" :key="locale" class="translation-locale">
      <legend>
        {{ t(`contentLocales.${locale.replace('-', '')}`) }}
        <small v-if="originalLocale === locale" class="field-hint">{{ t('contentLocales.original') }}</small>
      </legend>
      <div v-for="field in fields" :key="field.key" class="field">
        <label :for="`${idPrefix}-${locale}-${field.key}`">{{ field.label }}</label>
        <InputText
          :id="`${idPrefix}-${locale}-${field.key}`"
          :model-value="value(locale, field.key)"
          :disabled="disabled"
          :required="originalLocale === locale && field.key === fields[0]?.key"
          fluid
          @update:model-value="update(locale, field.key, $event ?? '')"
        />
      </div>
      <slot name="locale" :locale="locale" />
    </fieldset>
  </div>
</template>

<style scoped lang="scss">
.translation-fields {
  display: grid;
  gap: var(--space-3);
}

.translation-locale {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  margin: 0;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);

  legend {
    padding: 0 var(--space-1);
    font-weight: 700;
  }
}

@media (min-width: $bp-sm) {
  .translation-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
