<script setup lang="ts">
/**
 * Writing or changing a recipe. The form holds every content language at
 * once; the recipe tab edits the original language, the steps tab the steps
 * with their ingredients, and the translation tab the other languages, so
 * one save sends all of it. A new recipe starts as a draft.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useConfirm } from 'openvue/useconfirm'

import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import {
  createRecipe,
  getPrivacySettings,
  getRecipeForEdit,
  listEquipment,
  listShareTargets,
  publishRecipe,
  updateRecipe,
  type PeerRef,
} from '@/features/recipes/api/recipes'
import DraftNotice from '@/features/recipes/components/DraftNotice.vue'
import EditorActions, { type EditorAction } from '@/features/recipes/components/EditorActions.vue'
import ImageUpload from '@/features/recipes/components/ImageUpload.vue'
import IngredientSummaryCard from '@/features/recipes/components/IngredientSummaryCard.vue'
import StepEditor from '@/features/recipes/components/StepEditor.vue'
import TranslationEditor from '@/features/recipes/components/TranslationEditor.vue'
import VisibilityPicker from '@/features/recipes/components/VisibilityPicker.vue'
import {
  addStep,
  editorFormFrom,
  emptyForm,
  mentionProblemOf,
  moveStep,
  removeStep,
  stepsWithStrayMentions,
  toRequest,
  upgradeDraft,
  validate,
  type EditorError,
  type EditorForm,
  type MentionProblem,
} from '@/features/recipes/composables/recipeEditorState'
import { useEditorDraft } from '@/features/recipes/composables/useEditorDraft'
import { errorCode, errorStatus } from '@/core/utils/errors'
import EmptyState from '@/shared/components/EmptyState.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import FieldSkeleton from '@/shared/components/skeleton/FieldSkeleton.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import RichTextEditor from '@/shared/components/richText/RichTextEditor.vue'
import { CONTENT_LOCALES, contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { effectiveDefault } from '@/shared/cookbook/privacyMode'
import type { ContentLocale, EquipmentResponse } from '@/shared/cookbook/types'
import UnitSelect from '@/shared/cookbook/UnitSelect.vue'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const resources = useCookbookResources()
const confirm = useConfirm()

const recipeId = computed(() => (route.params.id ? String(route.params.id) : null))
const isNew = computed(() => recipeId.value === null)

const form = reactive<EditorForm>(emptyForm(contentLocaleOf(locale.value)))
const status = ref<'draft' | 'published'>('draft')
const loading = ref(false)
const saving = ref(false)
const errors = ref<EditorError[]>([])
const tab = ref('recipe')
// Unsaved changes stay on the device per user and recipe until saved or cancelled.
const draft = useEditorDraft(form, () => `recipe:${recipeId.value ?? 'new'}`, upgradeDraft, {
  ids: (f) => [f.cover_image_id, ...f.steps.map((step) => step.image_id)],
  drop: (f, missing) => {
    if (f.cover_image_id && missing.has(f.cover_image_id)) f.cover_image_id = null
    for (const step of f.steps) if (step.image_id && missing.has(step.image_id)) step.image_id = null
  },
})
// Whether the instance lets this user pick who reads the recipe.
const visibilityLocked = ref(false)
// The visibility that applied when the recipe was loaded, to tell when a
// save makes it public for the first time.
const loadedEffective = ref<string | null>(null)
// Whether the instance offers "public"; a recipe stored as public stays so
// while it is off and the picker says that it reads as instance meanwhile.
const publicAllowed = ref(false)
// Whether peering is on, so "paired instances" is offered; a recipe stored
// as peers stays so while it is off and the picker says that it reads as
// instance meanwhile.
const publicInfo = usePublicInfoStore()
const peering = computed(() => publicInfo.info?.features.peering ?? false)
// The paired instances the user may share with, and those the recipe goes
// to already (kept as options even when one may not be picked anew).
const shareTargets = ref<PeerRef[]>([])
const sharedPeers = ref<PeerRef[]>([])
const peerTargets = computed(() => {
  const known = new Map(shareTargets.value.map((p) => [p.id, p]))
  for (const peer of sharedPeers.value) if (!known.has(peer.id)) known.set(peer.id, peer)
  return [...known.values()]
})
// A copy of a recipe from another instance stays here: no public, no peers.
const peerCapped = ref(false)
// Direct sub-recipes that do not go to every instance the recipe goes to.
const peerHiddenIds = ref<string[]>([])
const peerHiddenNames = computed(() => subRecipeNames(peerHiddenIds.value))
// The recipe exists but the reader may not change it, or it is not there for them.
const blocked = ref<'forbidden' | 'missing' | null>(null)

const canCreateIngredient = computed(() =>
  currentUser.hasPermission(Permission.WRITE_INGREDIENTS),
)
const original = computed(() => form.original_locale)
const units = computed(() => resources.units.value)
const tagOptions = computed(() =>
  resources.tags.value.map((tag) => ({ id: tag.id, name: tag.name })),
)
const localeOptions = computed(() =>
  CONTENT_LOCALES.map((l) => ({ value: l, label: t(`contentLocales.${l.replace('-', '')}`) })),
)
const difficultyOptions = computed(() =>
  (['easy', 'medium', 'hard'] as const).map((d) => ({ value: d, label: t(`recipes.difficulty.${d}`) })),
)
// Every step's lines, which the steps' pickers compare with the declared list.
const stepLines = computed(() => form.steps.flatMap((s) => s.ingredients))
// The equipment catalogue for the steps' pickers and `@` suggestions.
const equipment = ref<EquipmentResponse[]>([])
// Where the backend's mention check refused a token, cleared on the next save.
const mentionProblem = ref<MentionProblem | null>(null)
// A refused token in a translation is marked in the translation tab, one in
// the original text in the steps tab.
const translationProblem = computed(() =>
  mentionProblem.value?.locale && mentionProblem.value.locale !== original.value
    ? { stepIndex: mentionProblem.value.stepIndex, locale: mentionProblem.value.locale as ContentLocale }
    : null,
)
const serverStepError = computed(() =>
  translationProblem.value ? null : (mentionProblem.value?.stepIndex ?? null),
)
const invalidSteps = computed(() => {
  const stray = errors.value.includes('mentionMissing') ? stepsWithStrayMentions(form) : []
  return form.steps.map(
    (s, i) =>
      (errors.value.includes('stepTextRequired') && s.text[original.value].trim() === '') ||
      stray.includes(i) ||
      serverStepError.value === i,
  )
})

// A new recipe starts at the user's own default, else the instance's, both
// read through the public and peering switches.
async function applyDefaultVisibility() {
  try {
    const privacy = await getPrivacySettings()
    publicAllowed.value = privacy.allow_public_recipes
    form.visibility = effectiveDefault(
      privacy,
      currentUser.user?.default_recipe_visibility,
      peering.value,
    )
    visibilityLocked.value = !privacy.users_may_change_visibility
  } catch (err) {
    toast.error(err)
  }
}

async function loadPublicAllowed() {
  try {
    publicAllowed.value = (await getPrivacySettings()).allow_public_recipes
  } catch {
    publicAllowed.value = false
  }
}

async function loadShareTargets() {
  try {
    shareTargets.value = await listShareTargets()
  } catch {
    shareTargets.value = []
  }
}

async function load() {
  void loadShareTargets()
  if (!recipeId.value) {
    await applyDefaultVisibility()
    draft.start(null)
    return
  }
  void loadPublicAllowed()
  loading.value = true
  try {
    const recipe = await getRecipeForEdit(recipeId.value)
    if (!recipe.can_edit) {
      blocked.value = 'forbidden'
      return
    }
    Object.assign(form, editorFormFrom(recipe))
    status.value = recipe.status === 'published' ? 'published' : 'draft'
    visibilityLocked.value = !recipe.can_change_visibility
    loadedEffective.value = recipe.effective_visibility
    sharedPeers.value = recipe.shared_peers ?? []
    peerCapped.value = recipe.peer_capped
    peerHiddenIds.value = recipe.peer_hidden_sub_recipe_ids ?? []
    draft.start(recipe.changed)
  } catch (err) {
    // A refusal gets a page of its own instead of an empty form and the raw message.
    const code = errorStatus(err)
    if (code === 403) blocked.value = 'forbidden'
    else if (code === 404) blocked.value = 'missing'
    else toast.error(err)
  } finally {
    loading.value = false
  }
}

async function save(publish = false) {
  mentionProblem.value = null
  errors.value = validate(form)
  if (errors.value.length) {
    tab.value =
      errors.value.includes('titleRequired') ||
      errors.value.includes('servingsInvalid') ||
      errors.value.includes('yieldIncomplete')
        ? 'recipe'
        : 'steps'
    return
  }
  saving.value = true
  try {
    const body = toRequest(form)
    const saved = recipeId.value
      ? await updateRecipe(recipeId.value, body)
      : await createRecipe(body)
    const lessVisible = saved.less_visible_sub_recipe_ids
    const isPublic = saved.effective_visibility === 'public'
    if (publish && saved.status !== 'published') {
      if (lessVisible.length && !(await confirmLessVisible(lessVisible, isPublic))) {
        toast.success(t('recipes.editor.saved'))
        // The recipe is saved as a draft and stays open, now under its id.
        draft.clear()
        await router.replace({ name: 'recipe-edit', params: { id: saved.id } })
        draft.start(saved.changed)
        return
      }
      await publishRecipe(saved.id)
    } else if (
      saved.status === 'published' &&
      isPublic &&
      loadedEffective.value !== 'public' &&
      lessVisible.length &&
      loadedEffective.value &&
      !(await confirmStillPublic(lessVisible))
    ) {
      // Undo: the recipe goes back to the visibility it had.
      form.visibility = loadedEffective.value as typeof form.visibility
      await updateRecipe(saved.id, toRequest(form))
    }
    draft.clear()
    toast.success(publish ? t('recipes.editor.published') : t('recipes.editor.saved'))
    await router.push({ name: 'recipe', params: { id: saved.id } })
  } catch (err) {
    // The backend's mention check says which step and language it refused.
    const problem = mentionProblemOf(err)
    if (problem) {
      mentionProblem.value = problem
      tab.value = problem.locale && problem.locale !== original.value ? 'translation' : 'steps'
    }
    // A chosen instance no longer takes recipes from here: the targets are
    // read again so the choice can be corrected.
    const code = errorCode(err)
    if (code === 'PeerShareNotAllowedError' || code === 'PeerNotFoundError') {
      tab.value = 'recipe'
      await loadShareTargets()
      toast.error(err, 'recipes.visibility.peerRefused')
      return
    }
    toast.error(err)
  } finally {
    saving.value = false
  }
}

function subRecipeNames(ids: string[]): string {
  const names = [...form.steps.flatMap((s) => s.ingredients), ...form.ingredients]
    .filter((i) => i.sub_recipe_id && ids.includes(i.sub_recipe_id))
    .map((i) => i.ingredient_name)
  return [...new Set(names)].join(', ')
}

// Publishing a recipe whose sub-recipes fewer people can read leaves those
// readers with "a recipe you don't have access to", so the cook decides. A
// public recipe names the sub-recipes visitors without an account miss.
function confirmLessVisible(ids: string[], isPublic = false): Promise<boolean> {
  const names = subRecipeNames(ids)
  return new Promise((resolve) => {
    confirm.require({
      header: isPublic ? t('recipes.editor.notPublicTitle') : t('recipes.editor.lessVisibleTitle'),
      message: isPublic
        ? t('recipes.editor.notPublic', { names })
        : t('recipes.editor.lessVisible', { names }),
      acceptProps: { label: t('recipes.editor.publishAnyway') },
      rejectProps: { label: t('recipes.editor.keepDraft'), text: true },
      accept: () => resolve(true),
      reject: () => resolve(false),
      onHide: () => resolve(false),
    })
  })
}

// A published recipe made public whose sub-recipes are not public: the
// cook keeps it public or takes the change back.
function confirmStillPublic(ids: string[]): Promise<boolean> {
  return new Promise((resolve) => {
    confirm.require({
      header: t('recipes.editor.notPublicTitle'),
      message: t('recipes.editor.notPublic', { names: subRecipeNames(ids) }),
      acceptProps: { label: t('recipes.editor.keepPublic') },
      rejectProps: { label: t('recipes.editor.undoPublic'), text: true },
      accept: () => resolve(true),
      reject: () => resolve(false),
      onHide: () => resolve(true),
    })
  })
}

// Cancel, save and, for a draft, publish, with the furthest-reaching one as
// the primary action.
const actions = computed<EditorAction[]>(() => {
  const cancelAction: EditorAction = { id: 'cancel', label: t('common.cancel'), variant: 'text', run: () => void cancel() }
  if (status.value === 'published') {
    return [
      cancelAction,
      { id: 'save', label: t('common.save'), icon: 'mdi mdi-content-save-outline', primary: true, run: () => void save(false) },
    ]
  }
  return [
    cancelAction,
    { id: 'save', label: t('recipes.editor.saveDraft'), icon: 'mdi mdi-content-save-outline', variant: 'outlined', run: () => void save(false) },
    { id: 'publish', label: t('recipes.editor.publish'), icon: 'mdi mdi-earth', primary: true, run: () => void save(true) },
  ]
})

async function cancel() {
  if (!(await draft.confirmLeave())) return
  draft.clear()
  if (recipeId.value) void router.push({ name: 'recipe', params: { id: recipeId.value } })
  else void router.push({ name: 'recipes' })
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
  <section class="editor">
    <PageHeader
      sticky
      :title="isNew ? t('recipes.editor.newTitle') : t('recipes.editor.editTitle')"
    >
      <EditorActions v-if="!blocked" :actions="actions" :busy="saving || loading" />
    </PageHeader>

    <ContentCard v-if="blocked">
      <EmptyState
        :message="blocked === 'forbidden' ? t('recipes.editor.forbidden') : t('recipes.detail.notFound')"
        :icon="blocked === 'forbidden' ? 'mdi mdi-pencil-off-outline' : 'mdi mdi-book-off-outline'"
      >
        <RouterLink
          v-if="blocked === 'forbidden' && recipeId"
          :to="{ name: 'recipe', params: { id: recipeId } }"
          custom
        >
          <template #default="{ navigate }">
            <Button :label="t('recipes.editor.backToRecipe')" severity="secondary" @click="navigate" />
          </template>
        </RouterLink>
        <RouterLink v-else :to="{ name: 'recipes' }" custom>
          <template #default="{ navigate }">
            <Button :label="t('recipes.detail.backToRecipes')" severity="secondary" @click="navigate" />
          </template>
        </RouterLink>
      </EmptyState>
    </ContentCard>

    <template v-else>
    <DraftNotice v-if="draft.restored.value" :draft="draft.restored.value" @discard="draft.discard()" />
    <Message v-if="errors.length" severity="error" class="editor-errors">
      <ul>
        <li v-for="error in errors" :key="error">{{ t(`recipes.editor.errors.${error}`) }}</li>
      </ul>
    </Message>

    <Tabs v-model:value="tab" scrollable class="editor-tabs">
      <ContentCard class="editor-tab-card">
        <TabList>
          <Tab value="recipe">{{ t('recipes.editor.tabs.recipe') }}</Tab>
          <Tab value="steps">{{ t('recipes.editor.tabs.steps', { n: form.steps.length }) }}</Tab>
          <Tab value="translation">{{ t('recipes.editor.tabs.translation') }}</Tab>
        </TabList>
      </ContentCard>
      <TabPanels>
        <TabPanel value="recipe">
          <ContentCard v-if="!loading" class="editor-card editor-grid">
            <div class="editor-column">
              <div class="field">
                <span id="editor-locale-label" class="field-label">{{ t('recipes.editor.originalLocale') }}</span>
                <SelectButton
                  v-model="form.original_locale"
                  :options="localeOptions"
                  option-label="label"
                  option-value="value"
                  :allow-empty="false"
                  aria-labelledby="editor-locale-label"
                />
                <small class="field-hint">{{ t('recipes.editor.originalLocaleHint') }}</small>
              </div>
              <div class="field">
                <label for="editor-title" class="field-label">{{ t('recipes.editor.title') }}</label>
                <InputText
                  id="editor-title"
                  v-model="form.text[original].title"
                  fluid
                  :invalid="errors.includes('titleRequired')"
                />
              </div>
              <div class="field">
                <span id="editor-description-label" class="field-label">{{ t('recipes.editor.description') }}</span>
                <RichTextEditor
                  :key="`description-${original}`"
                  v-model="form.text[original].description"
                  labelledby="editor-description-label"
                  :rows="3"
                />
              </div>
              <div class="field">
                <span id="editor-tips-label" class="field-label">{{ t('recipes.editor.tips') }}</span>
                <RichTextEditor
                  :key="`tips-${original}`"
                  v-model="form.text[original].tips"
                  labelledby="editor-tips-label"
                  :rows="2"
                />
              </div>
              <VisibilityPicker
                v-model:visibility="form.visibility"
                v-model:shared-user-ids="form.shared_user_ids"
                v-model:shared-group-ids="form.shared_group_ids"
                v-model:shared-peer-ids="form.shared_peer_ids"
                :locked="visibilityLocked"
                :public-allowed="publicAllowed"
                :peering="peering"
                :peer-targets="peerTargets"
                :capped="peerCapped"
                :peer-hidden-names="peerHiddenNames"
              />
              <div class="field">
                <span id="editor-tags-label" class="field-label">{{ t('recipes.editor.tags') }}</span>
                <MultiSelect
                  v-model="form.tag_ids"
                  :options="tagOptions"
                  option-label="name"
                  option-value="id"
                  display="chip"
                  filter
                  fluid
                  aria-labelledby="editor-tags-label"
                />
              </div>
            </div>
            <div class="editor-column">
              <ImageUpload v-model="form.cover_image_id" :label="t('recipes.editor.cover')" />
              <div class="editor-numbers">
                <div class="field">
                  <label for="editor-servings" class="field-label">{{ t('recipes.editor.baseServings') }}</label>
                  <InputNumber
                    v-model="form.base_servings"
                    input-id="editor-servings"
                    :min="1"
                    :max="99"
                    show-buttons
                    fluid
                    :invalid="errors.includes('servingsInvalid')"
                  />
                </div>
                <div class="field">
                  <span id="editor-difficulty-label" class="field-label">{{ t('recipes.editor.difficulty') }}</span>
                  <Select
                    v-model="form.difficulty"
                    :options="difficultyOptions"
                    option-label="label"
                    option-value="value"
                    fluid
                    aria-labelledby="editor-difficulty-label"
                  />
                </div>
                <div class="field">
                  <label for="editor-prep" class="field-label">{{ t('recipes.time.prep') }}</label>
                  <InputNumber v-model="form.prep_minutes" input-id="editor-prep" :min="0" :suffix="` ${t('recipes.editor.minutesSuffix')}`" fluid />
                </div>
                <div class="field">
                  <label for="editor-cook" class="field-label">{{ t('recipes.time.cook') }}</label>
                  <InputNumber v-model="form.cook_minutes" input-id="editor-cook" :min="0" :suffix="` ${t('recipes.editor.minutesSuffix')}`" fluid />
                </div>
                <div class="field">
                  <label for="editor-rest" class="field-label">{{ t('recipes.time.rest') }}</label>
                  <InputNumber v-model="form.rest_minutes" input-id="editor-rest" :min="0" :suffix="` ${t('recipes.editor.minutesSuffix')}`" fluid />
                </div>
              </div>
              <div class="editor-yield">
                <div class="field">
                  <label for="editor-yield" class="field-label">{{ t('recipes.editor.yield') }}</label>
                  <InputNumber
                    v-model="form.yield_amount"
                    input-id="editor-yield"
                    :min="0"
                    :max-fraction-digits="2"
                    fluid
                    :invalid="errors.includes('yieldIncomplete')"
                  />
                </div>
                <div class="field">
                  <span id="editor-yield-unit-label" class="field-label">{{ t('recipes.editor.yieldUnit') }}</span>
                  <UnitSelect
                    v-model="form.yield_unit_id"
                    :units="units"
                    show-clear
                    fluid
                    :invalid="errors.includes('yieldIncomplete')"
                    aria-labelledby="editor-yield-unit-label"
                  />
                </div>
                <small class="field-hint editor-yield-hint">{{ t('recipes.editor.yieldHint') }}</small>
              </div>
              <div class="field">
                <label for="editor-source-name" class="field-label">{{ t('recipes.editor.sourceName') }}</label>
                <InputText id="editor-source-name" v-model="form.source_name" fluid />
              </div>
              <div class="field">
                <label for="editor-source-url" class="field-label">{{ t('recipes.editor.sourceUrl') }}</label>
                <InputText id="editor-source-url" v-model="form.source_url" type="url" fluid />
              </div>
            </div>
          </ContentCard>
          <SkeletonRegion v-else class="card editor-card editor-grid" testid="recipe-editor-skeleton">
            <div class="editor-column">
              <FieldSkeleton control="2.5rem" label-width="30%" />
              <FieldSkeleton label-width="20%" />
              <FieldSkeleton control="8rem" label-width="30%" />
              <FieldSkeleton control="6rem" label-width="20%" />
              <FieldSkeleton label-width="15%" />
            </div>
            <div class="editor-column">
              <div class="editor-numbers">
                <FieldSkeleton v-for="n in 5" :key="n" label-width="60%" />
              </div>
              <FieldSkeleton label-width="40%" />
              <FieldSkeleton label-width="40%" />
            </div>
          </SkeletonRegion>
        </TabPanel>

        <TabPanel value="steps">
          <div class="editor-steps">
            <IngredientSummaryCard
              v-model:form="form"
              :locale="original"
              :units="units"
              :can-create-ingredient="canCreateIngredient"
              :recipe-id="recipeId"
            />
            <StepEditor
              v-for="(step, i) in form.steps"
              :key="step.key"
              :step="step"
              :index="i"
              :count="form.steps.length"
              :locale="original"
              :units="units"
              :can-create-ingredient="canCreateIngredient"
              :equipment="equipment"
              :invalid="invalidSteps[i]"
              :recipe-id="recipeId"
              :declared="form.ingredients"
              :recipe-lines="stepLines"
              @move="(d) => moveStep(form, i, d)"
              @remove="removeStep(form, i)"
              @insert-after="addStep(form, i)"
            />
            <Button
              :label="t('recipes.editor.addStep')"
              icon="mdi mdi-plus"
              severity="secondary"
              outlined
              @click="addStep(form)"
            />
          </div>
        </TabPanel>

        <TabPanel value="translation">
          <TranslationEditor :form="form" :problem="translationProblem" />
        </TabPanel>
      </TabPanels>
    </Tabs>

    </template>
  </section>
</template>

<style scoped lang="scss">
.editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-bottom: var(--space-6);
}

.editor-errors ul {
  margin: 0;
  padding-left: var(--space-5);
}

.editor-grid,
.editor-column {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.editor-numbers {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.editor-yield {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2) var(--space-3);
}

.editor-yield-hint {
  grid-column: 1 / -1;
}

.editor-steps {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

// The tab switcher sits in a card of its own above the panels, and the
// panels lay their content straight onto the page: the recipe tab in one
// card, the steps and translations in cards of their own.
.editor-tabs {
  --p-tabs-tabpanel-padding: 0;

  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

// The card's own border frames the tabs, so the list drops its rule.
.editor-tab-card {
  --p-tabs-tablist-border-width: 0;

  height: auto;
  padding: 0 var(--space-2);
  overflow: hidden;
}

.editor-card {
  height: auto;
}

@media (min-width: $bp-md) {
  .editor-grid {
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
    gap: var(--space-6);
  }

  .editor-numbers {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
