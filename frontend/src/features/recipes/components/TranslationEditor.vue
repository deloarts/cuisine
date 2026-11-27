<script setup lang="ts">
/**
 * Translating a recipe by hand: pick a language other than the original and
 * write its title, texts, steps and the notes of ingredients and equipment
 * next to the original. Anything left empty falls back to the original when
 * read; the translation counts once it has a title. A step whose mentions
 * the backend refused in one language opens that language, marked.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  lineMentions,
  translationState,
  type EditorForm,
} from '@/features/recipes/composables/recipeEditorState'
import RichText from '@/shared/components/richText/RichText.vue'
import RichTextEditor from '@/shared/components/richText/RichTextEditor.vue'
import type { MentionSource } from '@/shared/components/richText/mentions'
import { CONTENT_LOCALES } from '@/shared/cookbook/contentLocale'
import type { ContentLocale } from '@/shared/cookbook/types'

// The parent hands in its reactive form and this component edits it in place;
// the model is never replaced, so no update event is needed.
const form = defineModel<EditorForm>('form', { required: true })
const props = withDefaults(
  defineProps<{ problem?: { stepIndex: number; locale: ContentLocale } | null }>(),
  { problem: null },
)
const { t } = useI18n()

const targets = computed(() => CONTENT_LOCALES.filter((l) => l !== form.value.original_locale))
const target = ref<ContentLocale>(targets.value[0] ?? 'de-AT')
watch(targets, (list) => {
  if (!list.includes(target.value) && list[0]) target.value = list[0]
})
watch(
  () => props.problem,
  (problem) => {
    if (problem && targets.value.includes(problem.locale)) target.value = problem.locale
  },
  { immediate: true },
)
const problemStep = computed(() =>
  props.problem && props.problem.locale === target.value ? props.problem.stepIndex : null,
)

const original = computed(() => form.value.original_locale)

// A translation keeps the original's mentions; `@` offers only the step's
// own lines and equipment, since a translation adds neither.
function translationMentions(step: EditorForm['steps'][number]): MentionSource {
  return {
    search: async (query) => {
      const q = query.trim().toLowerCase()
      return lineMentions(step).filter((r) => r.name.toLowerCase().includes(q))
    },
  }
}
const label = (l: string) => t(`contentLocales.${l.replace('-', '')}`)
const options = computed(() =>
  targets.value.map((l) => ({
    value: l,
    label: `${label(l)} · ${t(`recipes.translation.state.${translationState(form.value, l)}`)}`,
  })),
)
</script>

<template>
  <div class="translation">
    <p class="hint">
      {{ t('recipes.translation.hint', { original: label(original) }) }}
    </p>
    <div class="field">
      <span id="translation-target-label" class="field-label">{{ t('recipes.translation.locale') }}</span>
      <SelectButton
        v-model="target"
        :options="options"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        aria-labelledby="translation-target-label"
      />
    </div>

    <section class="translation-block">
      <div class="field">
        <label for="tr-title" class="field-label">{{ t('recipes.editor.title') }}</label>
        <p class="translation-original">{{ form.text[original].title || '–' }}</p>
        <InputText id="tr-title" v-model="form.text[target].title" fluid />
      </div>
      <div class="field">
        <span id="tr-description-label" class="field-label">{{ t('recipes.editor.description') }}</span>
        <RichText
          v-if="form.text[original].description"
          class="translation-original"
          :text="form.text[original].description"
        />
        <RichTextEditor
          :key="`tr-description-${target}`"
          v-model="form.text[target].description"
          labelledby="tr-description-label"
          :rows="2"
        />
      </div>
      <div v-if="form.text[original].tips" class="field">
        <span id="tr-tips-label" class="field-label">{{ t('recipes.editor.tips') }}</span>
        <RichText class="translation-original" :text="form.text[original].tips" />
        <RichTextEditor
          :key="`tr-tips-${target}`"
          v-model="form.text[target].tips"
          labelledby="tr-tips-label"
          :rows="2"
        />
      </div>
    </section>

    <section
      v-for="(step, i) in form.steps"
      :key="step.key"
      class="translation-block"
      :class="{ 'translation-block--invalid': problemStep === i }"
    >
      <h3>{{ t('recipes.detail.step', { n: i + 1 }) }}</h3>
      <div class="field">
        <span :id="`tr-step-${step.key}-label`" class="field-label">{{ t('recipes.editor.stepText') }}</span>
        <RichText class="translation-original" :text="step.text[original] || '–'" />
        <RichTextEditor
          :key="`tr-step-${step.key}-${target}`"
          v-model="step.text[target]"
          :labelledby="`tr-step-${step.key}-label`"
          :rows="3"
          mentionable
          :mentions="translationMentions(step)"
        />
      </div>
      <template v-for="row in step.ingredients" :key="row.key">
        <div v-if="row.notes[original]" class="field">
          <label :for="`tr-note-${row.key}`" class="field-label">
            {{ t('recipes.translation.note', { name: row.ingredient_name }) }}
          </label>
          <p class="translation-original">{{ row.notes[original] }}</p>
          <InputText :id="`tr-note-${row.key}`" v-model="row.notes[target]" fluid />
        </div>
      </template>
      <template v-for="row in step.equipment" :key="row.key">
        <div v-if="row.notes[original]" class="field">
          <label :for="`tr-eq-note-${row.key}`" class="field-label">
            {{ t('recipes.translation.note', { name: row.equipment_name }) }}
          </label>
          <p class="translation-original">{{ row.notes[original] }}</p>
          <InputText :id="`tr-eq-note-${row.key}`" v-model="row.notes[target]" fluid />
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped lang="scss">
.translation {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.translation-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
}

.translation-block--invalid {
  border-color: var(--p-red-400);
}

.translation-original {
  padding: var(--space-2) var(--space-3);
  border-left: 3px solid var(--p-content-border-color);
  color: var(--p-text-muted-color);
}
</style>
