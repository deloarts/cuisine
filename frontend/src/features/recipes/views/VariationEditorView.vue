<script setup lang="ts">
/**
 * Writing or changing a variation of a recipe: a name, a short note, the
 * private flag and the changes, each against a step of the recipe as it is
 * now. Anyone who may write recipes and can read the recipe adds one; only
 * the author changes it. Phone first: one column of change cards, with save
 * and cancel in the page header.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import {
  createVariation,
  getRecipe,
  getVariation,
  listEquipment,
  updateVariation,
  type RecipeDetailResponse,
  type VariationChangeKind,
} from '@/features/recipes/api/recipes'
import DraftNotice from '@/features/recipes/components/DraftNotice.vue'
import EditorActions, { type EditorAction } from '@/features/recipes/components/EditorActions.vue'
import VariationChangeEditor from '@/features/recipes/components/VariationChangeEditor.vue'
import {
  CHANGE_KINDS,
  MAX_CHANGES,
  emptyVariationForm,
  incompleteChanges,
  newChange,
  toVariationRequest,
  validateVariation,
  variationFormFrom,
  type VariationError,
  type VariationForm,
} from '@/features/recipes/composables/variationEditorState'
import { useEditorDraft } from '@/features/recipes/composables/useEditorDraft'
import EmptyState from '@/shared/components/EmptyState.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import FieldSkeleton from '@/shared/components/skeleton/FieldSkeleton.vue'
import SkeletonLines from '@/shared/components/skeleton/SkeletonLines.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import { CONTENT_LOCALES, contentLocaleOf } from '@/shared/cookbook/contentLocale'
import type { ContentLocale, EquipmentResponse } from '@/shared/cookbook/types'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const resources = useCookbookResources()

const recipeId = computed(() => String(route.params.id))
const variationId = computed(() => (route.params.variationId ? String(route.params.variationId) : null))

const form = reactive<VariationForm>(emptyVariationForm(contentLocaleOf(locale.value)))
const recipe = ref<RecipeDetailResponse | null>(null)
const equipment = ref<EquipmentResponse[]>([])
const loading = ref(true)
const saving = ref(false)
const blocked = ref<'notYours' | 'missing' | null>(null)
const errors = ref<VariationError[]>([])
// Unsaved changes stay on the device per user, recipe and variation until
// saved or cancelled.
const draft = useEditorDraft(form, () => `variation:${recipeId.value}:${variationId.value ?? 'new'}`)
const invalid = computed(() => (errors.value.includes('changeIncomplete') ? incompleteChanges(form) : []))

const canCreateIngredient = computed(() => currentUser.hasPermission(Permission.WRITE_INGREDIENTS))
const localeOptions = computed(() =>
  CONTENT_LOCALES.map((l) => ({ value: l, label: t(`contentLocales.${l.replace('-', '')}`) })),
)

// The recipe is read in the variation's language, so step texts and line
// names match what the variation is written against.
async function loadRecipe() {
  recipe.value = await getRecipe(recipeId.value, { locale: form.locale })
}

async function load() {
  let base: string | null = null
  loading.value = true
  try {
    if (variationId.value) {
      const variation = await getVariation(recipeId.value, variationId.value)
      if (!variation.can_edit) {
        blocked.value = 'notYours'
        return
      }
      Object.assign(form, variationFormFrom(variation))
      base = variation.changed
    }
    await loadRecipe()
    const readIn = form.locale
    // A new variation is written against the recipe as it is now.
    draft.start(base ?? recipe.value?.changed ?? null)
    // A restored draft in another language reads the recipe in that one.
    if (form.locale !== readIn) await loadRecipe()
  } catch {
    blocked.value = 'missing'
  } finally {
    loading.value = false
  }
}

async function changeLocale(next: ContentLocale) {
  form.locale = next
  try {
    await loadRecipe()
  } catch (err) {
    toast.error(err)
  }
}

// The saved version may be in another language, so the recipe is read again.
async function discardDraft() {
  const readIn = form.locale
  draft.discard()
  if (form.locale !== readIn) await changeLocale(form.locale)
}

function addChange(kind: VariationChangeKind) {
  form.changes.push(newChange(kind, kind === 'swap' ? null : kind === 'extra_step' ? recipe.value?.steps.length ?? 0 : 1))
}

async function save() {
  errors.value = validateVariation(form)
  if (errors.value.length) return
  saving.value = true
  try {
    const body = toVariationRequest(form)
    const saved = variationId.value
      ? await updateVariation(recipeId.value, variationId.value, body)
      : await createVariation(recipeId.value, body)
    draft.clear()
    toast.success(t('recipes.variations.editor.saved'))
    await router.push({ name: 'recipe', params: { id: recipeId.value }, query: { variation: saved.id } })
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

const actions = computed<EditorAction[]>(() => [
  { id: 'cancel', label: t('common.cancel'), variant: 'text', run: () => void cancel() },
  {
    id: 'save',
    label: t('recipes.variations.editor.save'),
    icon: 'mdi mdi-content-save-outline',
    primary: true,
    run: () => void save(),
  },
])

async function cancel() {
  if (!(await draft.confirmLeave())) return
  draft.clear()
  void router.push({
    name: 'recipe',
    params: { id: recipeId.value },
    query: variationId.value ? { variation: variationId.value } : {},
  })
}

onMounted(() => {
  void resources.load().catch((err: unknown) => toast.error(err))
  listEquipment()
    .then((items) => (equipment.value = items))
    .catch((err: unknown) => toast.error(err))
  void load()
})
</script>

<template>
  <section class="variation-editor">
    <PageHeader
      sticky
      :title="variationId ? t('recipes.variations.editor.editTitle') : t('recipes.variations.editor.newTitle')"
    >
      <EditorActions v-if="!blocked && !loading && recipe" :actions="actions" :busy="saving" />
    </PageHeader>

    <ContentCard v-if="blocked">
      <EmptyState
        :message="blocked === 'notYours' ? t('recipes.variations.editor.notYours') : t('recipes.detail.notFound')"
        icon="mdi mdi-source-branch-remove"
      >
        <Button :label="t('recipes.editor.backToRecipe')" severity="secondary" @click="cancel" />
      </EmptyState>
    </ContentCard>

    <SkeletonRegion v-else-if="loading" class="variation-editor-skeleton" testid="variation-editor-skeleton">
      <Skeleton width="45%" height="1rem" />
      <SkeletonLines :lines="2" />
      <ContentCard class="variation-editor-meta">
        <FieldSkeleton label-width="20%" />
        <FieldSkeleton control="4rem" label-width="25%" />
        <FieldSkeleton control="2.5rem" label-width="30%" />
        <Skeleton width="12rem" height="1.5rem" />
      </ContentCard>
      <Skeleton width="30%" height="1.5rem" />
    </SkeletonRegion>

    <template v-else-if="recipe">
      <p class="variation-editor-of">
        {{ t('recipes.variations.editor.of', { title: recipe.title }) }}
      </p>
      <p class="hint">{{ t('recipes.variations.editor.hint') }}</p>
      <DraftNotice v-if="draft.restored.value" :draft="draft.restored.value" @discard="discardDraft" />

      <Message v-if="errors.length" severity="error">
        <ul class="variation-editor-errors">
          <li v-for="error in errors" :key="error">{{ t(`recipes.variations.editor.errors.${error}`) }}</li>
        </ul>
      </Message>

      <ContentCard class="variation-editor-meta">
        <div class="field">
          <label for="variation-name" class="field-label">{{ t('recipes.variations.editor.name') }}</label>
          <InputText
            id="variation-name"
            v-model="form.name"
            maxlength="120"
            :placeholder="t('recipes.variations.editor.namePlaceholder')"
            :invalid="errors.includes('nameRequired') && !form.name.trim()"
            fluid
          />
        </div>
        <div class="field">
          <label for="variation-note" class="field-label">{{ t('recipes.variations.editor.note') }}</label>
          <Textarea
            id="variation-note"
            v-model="form.note"
            maxlength="1000"
            rows="2"
            auto-resize
            :placeholder="t('recipes.variations.editor.notePlaceholder')"
            fluid
          />
        </div>
        <div class="field">
          <span id="variation-locale-label" class="field-label">{{ t('recipes.variations.editor.locale') }}</span>
          <SelectButton
            :model-value="form.locale"
            :options="localeOptions"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            aria-labelledby="variation-locale-label"
            @update:model-value="changeLocale"
          />
        </div>
        <div class="variation-editor-switch">
          <ToggleSwitch v-model="form.private" input-id="variation-private" />
          <label for="variation-private">{{ t('recipes.variations.editor.private') }}</label>
        </div>
        <small class="field-hint">{{ t('recipes.variations.editor.privateHint') }}</small>
      </ContentCard>

      <h2 class="variation-editor-title">{{ t('recipes.variations.editor.changes', { n: form.changes.length }) }}</h2>
      <p v-if="!form.changes.length" class="hint">{{ t('recipes.variations.editor.noChanges') }}</p>
      <VariationChangeEditor
        v-for="(change, i) in form.changes"
        :key="change.key"
        v-model:change="form.changes[i]!"
        :index="i"
        :recipe="recipe"
        :units="resources.units.value"
        :equipment="equipment"
        :can-create-ingredient="canCreateIngredient"
        :invalid="invalid.includes(i)"
        @remove="form.changes.splice(i, 1)"
      />

      <div v-if="form.changes.length < MAX_CHANGES" class="variation-editor-add">
        <h3 class="field-label">{{ t('recipes.variations.editor.addChange') }}</h3>
        <div class="variation-editor-kinds">
          <Button
            v-for="kind in CHANGE_KINDS"
            :key="kind"
            :label="t(`recipes.variations.editor.kinds.${kind}`)"
            icon="mdi mdi-plus"
            severity="secondary"
            outlined
            :data-testid="`add-${kind}`"
            @click="addChange(kind)"
          />
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped lang="scss">
.variation-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-bottom: var(--space-6);
}

.variation-editor-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.variation-editor-of {
  font-weight: 700;
}

.variation-editor-errors {
  margin: 0;
  padding-left: var(--space-4);
}

.variation-editor-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: auto;
}

.variation-editor-switch {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.variation-editor-title {
  font-size: var(--font-size-2xl);
}

.variation-editor-add {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

// One full-width button per kind on a phone, side by side when there is room.
.variation-editor-kinds {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-2);
}

@media (min-width: $bp-sm) {
  .variation-editor-kinds {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
