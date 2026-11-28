<script setup lang="ts">
/**
 * A recipe as a cook reads it: the photo, what it takes, the ingredients
 * scaled to the chosen servings, the steps each with their own ingredients,
 * nutrition, and the reader's own warnings, rating and notes. It loads the
 * recipe once at its base servings and scales on the client.
 *
 * A recipe with variations offers a switch between the original and each
 * variation; a chosen variation is shown as the backend applies it, with
 * its changed parts marked. On the original, each step says which
 * variations do it differently.
 *
 * Printing the page (the Print action or the browser's own print) puts only
 * the recipe on paper, as it is on screen: the chosen servings, language and
 * variation, without the page's controls, the reader's own layer or the
 * comments of other cooks, and with a QR code that opens it again.
 *
 * A mirror, a recipe a paired instance shares with this one, is read only:
 * its badge opens a dialog that names its source and links there, it offers
 * no editing, publishing, deleting or export, and it shows the lines this
 * instance keeps as text in their steps. "Copy as my recipe" makes a local
 * copy that stays here.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import type { MenuItem } from 'openvue/menuitem'
import { useConfirm } from 'openvue/useconfirm'

import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import {
  copyRecipe,
  deleteVariation,
  exportRecipe,
  getRecipe,
  listCoEditors,
  listCopies,
  listRecipeCookEvents,
  listVariations,
  publishRecipe,
  setFavourite,
  unpublishRecipe,
  viewVariation,
  type CookEventResponse,
  type PersonRef,
  type RecipeCopyResponse,
  type RecipeDetailResponse,
  type VariationResponse,
  type VariationViewResponse,
} from '@/features/recipes/api/recipes'
import AddToListDialog from '@/features/recipes/components/AddToListDialog.vue'
import AdoptVariationDialog from '@/features/recipes/components/AdoptVariationDialog.vue'
import CoEditorsDialog from '@/features/recipes/components/CoEditorsDialog.vue'
import CookedDialog from '@/features/recipes/components/CookedDialog.vue'
import VariationChangeSummary from '@/features/recipes/components/VariationChangeSummary.vue'
import VariationSwitch from '@/features/recipes/components/VariationSwitch.vue'
import {
  authorName,
  lineMarks,
  markerAt,
  staleStep,
  stepDifferences,
  versionFromQuery,
} from '@/features/recipes/utils/variations'
import DeleteRecipeDialog from '@/features/recipes/components/DeleteRecipeDialog.vue'
import EquipmentList from '@/features/recipes/components/EquipmentList.vue'
import IngredientLines from '@/features/recipes/components/IngredientLines.vue'
import NotePanel from '@/features/recipes/components/NotePanel.vue'
import NutritionPanel from '@/features/recipes/components/NutritionPanel.vue'
import RecipePrintQr from '@/features/recipes/components/RecipePrintQr.vue'
import RatingPanel from '@/features/recipes/components/RatingPanel.vue'
import ServingsStepper from '@/features/recipes/components/ServingsStepper.vue'
import WarningBanner from '@/features/recipes/components/WarningBanner.vue'
import { cuiFileName } from '@/features/recipes/utils/exchange'
import { scaleFactor, scaleIngredients } from '@/features/recipes/utils/scaling'
import EmptyState from '@/shared/components/EmptyState.vue'
import { imageUrl } from '@/shared/components/recipes/recipeImage'
import RecipeDuration from '@/shared/components/recipes/RecipeDuration.vue'
import RichText from '@/shared/components/richText/RichText.vue'
import UserAvatar from '@/shared/components/UserAvatar.vue'
import ScrollFade from '@/shared/components/ScrollFade.vue'
import { downloadBlob } from '@/shared/composables/fileTransfer'
import { formatDay, isoDay } from '@/features/recipes/utils/dates'
import { useKeepScreenOn } from '@/shared/composables/useKeepScreenOn'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import type { ContentLocale } from '@/shared/cookbook/types'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatAmount, unitLabel } from '@/features/recipes/utils/scaling'
import { useAmountFormat } from '@/features/recipes/composables/useAmountFormat'
import { lineResolver } from '@/features/recipes/utils/mentionResolver'
import { formatSeason, monthName } from '@/shared/cookbook/season'
import { groupEquipmentNeeds, missingNeeds } from '@/features/recipes/utils/equipment'
import {
  allPlainEquipment,
  attributionParams,
  extraIngredients,
  mergeStepLines,
  plainEquipmentOf,
} from '@/features/recipes/utils/mirrors'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t, locale } = useI18n()
const { format: formatNeed } = useAmountFormat()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const confirm = useConfirm()

// The original as the backend derives it, and the chosen variation applied.
const base = ref<RecipeDetailResponse | null>(null)
const view = ref<VariationViewResponse | null>(null)
const recipe = computed(() => view.value?.recipe ?? base.value)
const variations = ref<VariationResponse[]>([])
const coEditors = ref<PersonRef[]>([])
const copies = ref<RecipeCopyResponse[] | null>(null)
const adoptOpen = ref(false)
const coEditorsOpen = ref(false)
const mirrorInfoOpen = ref(false)
const copying = ref(false)
const exporting = ref(false)
const loading = ref(true)
const notFound = ref(false)
const servings = ref(1)
// Recipe text follows the reader's UI language; the server falls back to
// the original language when the recipe has no translation into it.
const contentLocale = computed<ContentLocale>(() => contentLocaleOf(locale.value))
const cookEvents = ref<CookEventResponse[]>([])
const cookedOpen = ref(false)
// A recipe is logged at most once a day, so once today's meal is in the
// calendar the button says so instead of offering a second one.
const cookedToday = computed(() => recipe.value?.last_cooked_by_me === isoDay())
const deleteOpen = ref(false)
const listOpen = ref(false)
// The cooked card lists everybody's meals or only the reader's own.
const onlyMine = ref(false)

const recipeId = computed(() => String(route.params.id))
// Dinner guests chosen in the recipe browser arrive in the URL; the answer
// only says whether someone won't like the recipe, never who or why.
const guests = computed(() => {
  const value = route.query.guest
  const list = Array.isArray(value) ? value : value ? [value] : []
  return list.filter((g): g is string => typeof g === 'string' && g !== '')
})

async function load() {
  loading.value = true
  notFound.value = false
  try {
    const next = await getRecipe(recipeId.value, {
      locale: contentLocale.value,
      guests: guests.value,
    })
    // Keep the chosen servings when only the language changed.
    if (!base.value || base.value.id !== next.id) servings.value = next.base_servings
    if (base.value?.id !== next.id) copies.value = null
    base.value = next
    void loadCookEvents()
    void loadCoEditors()
    await loadVariations()
  } catch (err) {
    base.value = null
    view.value = null
    notFound.value = true
    toast.error(err)
  } finally {
    loading.value = false
  }
}

async function loadCookEvents() {
  try {
    cookEvents.value = (await listRecipeCookEvents(recipeId.value, onlyMine.value)).slice(0, 5)
  } catch {
    cookEvents.value = []
  }
}

// The variations the reader can see, then the chosen one applied.
async function loadVariations() {
  try {
    variations.value = await listVariations(recipeId.value)
  } catch {
    variations.value = []
  }
  await loadView()
}

const version = computed(() => versionFromQuery(route.query.variation, variations.value))
const variation = computed(() => variations.value.find((v) => v.id === version.value) ?? null)

async function loadView() {
  if (!version.value) {
    view.value = null
    return
  }
  try {
    view.value = await viewVariation(recipeId.value, version.value, {
      locale: contentLocale.value,
      guests: guests.value,
    })
  } catch (err) {
    view.value = null
    toast.error(err)
  }
}

function chooseVersion(id: string | null) {
  const query = { ...route.query }
  if (id) query.variation = id
  else delete query.variation
  void router.replace({ query })
}

async function loadCoEditors() {
  coEditors.value = []
  if (!base.value?.can_edit) return
  try {
    coEditors.value = await listCoEditors(recipeId.value)
  } catch {
    coEditors.value = []
  }
}

watch(
  recipeId,
  () => void load(),
  { immediate: true },
)
watch(contentLocale, () => void load())
watch(guests, () => void load())
// Switching versions reads the applied variation; a reload reads it itself.
watch(
  () => route.query.variation,
  (next, previous) => {
    if (next !== previous && base.value) void loadView()
  },
)
watch(onlyMine, () => void loadCookEvents())

const factor = computed(() =>
  recipe.value ? scaleFactor(servings.value, recipe.value.base_servings) : 1,
)
const ingredients = computed(() =>
  recipe.value
    ? scaleIngredients([...recipe.value.ingredients, ...extraIngredients(mirror.value)], factor.value)
    : [],
)
// A mirror's details: where it comes from and the lines kept as text.
const mirror = computed(() => recipe.value?.mirror_details ?? base.value?.mirror_details ?? null)
const isMirror = computed(() => !!(base.value?.mirror ?? base.value?.mirror_details))
const attribution = computed(() => {
  const source = base.value?.mirror ?? mirror.value
  if (!source) return ''
  const { key, params } = attributionParams(source)
  return t(key, params)
})
// The author's name and avatar at the source, when the source sends them.
const mirrorAuthor = computed(() => base.value?.mirror ?? mirror.value)
const steps = computed(() =>
  (recipe.value?.steps ?? []).map((step, s) => {
    // The source step a shown step stands for: itself on the original, the
    // step a variation's step came from otherwise (none for an added step).
    const origin = view.value ? markerAt(markers.value, step.position)?.origin_step : step.position
    const sourceIndex = origin ? origin - 1 : view.value ? null : s
    const merged = mergeStepLines(
      step.ingredients,
      mirror.value,
      sourceIndex,
      lineMarks(markerAt(markers.value, step.position), step.ingredients.length),
    )
    return {
      ...step,
      ingredients: scaleIngredients(step.ingredients, factor.value),
      shownLines: scaleIngredients(merged.items, factor.value),
      shownMarks: merged.marks,
      plainEquipment: plainEquipmentOf(mirror.value, sourceIndex),
    }
  }),
)
// The sub-recipes this one needs, scaled like every other amount.
const needs = computed(() =>
  (recipe.value?.needs ?? []).map((need) => ({
    ...need,
    amount: need.amount === null ? null : need.amount * factor.value,
    batches: need.batches * factor.value,
  })),
)
const isOwner = computed(
  () => !!base.value?.owner && base.value.owner.id === currentUser.user?.id,
)
const isCoEditor = computed(() => coEditors.value.some((p) => p.id === currentUser.user?.id))
const canWrite = computed(() => currentUser.hasPermission(Permission.WRITE_RECIPES))
// What each variation does differently in a step of the original.
const differences = computed(() =>
  view.value ? [] : steps.value.map((step) => stepDifferences(variations.value, step)),
)
const markers = computed(() => view.value?.steps ?? [])
const staleNotes = computed(() => variation.value?.stale_steps ?? [])
function variationBy(v: VariationResponse) {
  if (v.mirrored) {
    const instance = base.value?.mirror?.instance_name ?? mirror.value?.instance_name ?? ''
    return v.source_author_name
      ? t('recipes.mirror.variationByAt', { name: v.source_author_name, instance })
      : t('recipes.mirror.variationFrom', { instance })
  }
  return t('recipes.variations.by', { name: authorName(v) ?? t('recipes.variations.formerMember') })
}
// Unknown allergens and markers come from a source that knows more than
// this release; they read "contains: X (unknown marker)".
const unknownAllergens = computed(() => recipe.value?.unknown_allergens ?? [])
const unknownMarkers = computed(() => recipe.value?.unknown_diet_markers ?? [])
// Draft ingredients nobody has checked yet keep the recipe from claiming a
// diet; the page names them, so the reader knows why no diet shows.
const unconfirmedNames = computed(() => {
  const r = recipe.value
  if (!r?.unconfirmed_ingredient_ids?.length) return []
  const ids = new Set(r.unconfirmed_ingredient_ids)
  const names = r.ingredients.filter((i) => i.ingredient_id !== null && ids.has(i.ingredient_id)).map((i) => i.name)
  return [...new Set(names)]
})
const sourceAllergens = computed(() => recipe.value?.source_allergens_added ?? [])
const plainEquipment = computed(() => allPlainEquipment(mirror.value))
const numberLocale = computed(() => (locale.value === 'deAT' ? 'de-AT' : 'en-GB'))
function needAmount(need: (typeof needs.value)[number]): string {
  if (need.amount !== null && need.unit) {
    const line = { ingredient_id: null, name: '', amount: need.amount, unit: need.unit, note: '' }
    return `${formatNeed(need.amount, numberLocale.value, need.unit)} ${unitLabel(line)}`
  }
  return t('recipes.subRecipes.batches', { n: formatAmount(need.batches, numberLocale.value) })
}
// The months in which every seasonal ingredient of the recipe is in season.
const seasonText = computed(() =>
  recipe.value?.season_months.length
    ? formatSeason(recipe.value.season_months, (m) => monthName(m, numberLocale.value))
    : '',
)
// "You'll need": the recipe's own equipment, then each sub-recipe's.
const equipmentGroups = computed(() => groupEquipmentNeeds(recipe.value?.equipment ?? []))
const missingCount = computed(
  () => new Set(missingNeeds(recipe.value?.equipment ?? []).map((n) => n.equipment.id)).size,
)
const warnIds = computed(() =>
  (recipe.value?.warnings ?? []).flatMap((w) => (w.ingredient_id ? [w.ingredient_id] : [])),
)
const cover = computed(() =>
  recipe.value?.cover_image_id ? imageUrl(recipe.value.cover_image_id, 'original') : null,
)
async function toggleFavourite() {
  if (!recipe.value) return
  const next = !recipe.value.is_favourite
  // The original and the applied variation are the same recipe to keep.
  const shown = [base.value, view.value?.recipe].filter((r): r is RecipeDetailResponse => !!r)
  shown.forEach((r) => (r.is_favourite = next))
  try {
    await setFavourite(recipe.value.id, next)
  } catch (err) {
    shown.forEach((r) => (r.is_favourite = !next))
    toast.error(err)
  }
}

function onRated(average: number | null, count: number, own: boolean) {
  if (!recipe.value) return
  recipe.value.rating_average = average
  recipe.value.rating_count = count
  if (!own) recipe.value.own_rating = null
  const rated = variation.value
  if (rated) {
    rated.rating_average = average
    rated.rating_count = count
  }
  void refreshOverall()
}

// The overall average over the recipe and its variations follows every rating.
async function refreshOverall() {
  try {
    const fresh = await getRecipe(recipeId.value, { locale: contentLocale.value })
    if (base.value && base.value.id === fresh.id) {
      base.value.rating_overall_average = fresh.rating_overall_average
      base.value.rating_overall_count = fresh.rating_overall_count
      if (!view.value) {
        base.value.rating_average = fresh.rating_average
        base.value.rating_count = fresh.rating_count
      }
    }
  } catch {
    // The overall line simply stays as it was.
  }
}

function confirmDeleteVariation(target: VariationResponse) {
  confirm.require({
    header: t('recipes.variations.delete'),
    message: t('recipes.variations.deleteConfirm', { name: target.name }),
    acceptProps: { label: t('common.delete'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void removeVariation(target),
  })
}

async function removeVariation(target: VariationResponse) {
  try {
    await deleteVariation(recipeId.value, target.id)
    toast.success(t('recipes.variations.deleted'))
    variations.value = variations.value.filter((v) => v.id !== target.id)
    chooseVersion(null)
  } catch (err) {
    toast.error(err)
  }
}

// Adopting changes the original, so the page reads it again.
async function onAdopted() {
  await load()
}

async function copyAsMine() {
  if (!base.value) return
  copying.value = true
  try {
    const copy = await copyRecipe(base.value.id)
    toast.success(t('recipes.copies.copied'))
    await router.push({ name: 'recipe-edit', params: { id: copy.id } })
  } catch (err) {
    toast.error(err)
  } finally {
    copying.value = false
  }
}

async function exportCui() {
  if (!base.value) return
  exporting.value = true
  try {
    downloadBlob(await exportRecipe(base.value.id), cuiFileName(base.value.title))
  } catch (err) {
    toast.error(err)
  } finally {
    exporting.value = false
  }
}

// The print stylesheet below decides what reaches the paper.
function printRecipe() {
  window.print()
}

async function showCopies() {
  if (copies.value) {
    copies.value = null
    return
  }
  try {
    copies.value = await listCopies(recipeId.value)
  } catch (err) {
    toast.error(err)
  }
}

function onCooked(event: CookEventResponse) {
  cookEvents.value = [event, ...cookEvents.value].slice(0, 5)
  if (recipe.value) {
    recipe.value.last_cooked = event.cooked_on
    recipe.value.last_cooked_by_me = event.cooked_on
  }
}

async function togglePublished() {
  if (!base.value) return
  try {
    if (base.value.status === 'draft') {
      await publishRecipe(base.value.id)
      toast.success(t('recipes.detail.published'))
    } else {
      await unpublishRecipe(base.value.id)
      toast.success(t('recipes.detail.unpublished'))
    }
    await load()
  } catch (err) {
    toast.error(err)
  }
}

async function onDeleted() {
  await router.push({ name: 'recipes' })
}

const dateLabel = (day: string) => formatDay(day, locale.value)

// The page's less frequent actions sit in a speed dial at the foot of the
// screen. Each one keeps the condition its button had, and the dial is left
// out when the reader may do none of them.
interface PageAction extends MenuItem {
  key: string
  label: string
  icon: string
  danger?: boolean
  busy?: boolean
}
const pageActions = computed<PageAction[]>(() => {
  const r = recipe.value
  if (!r) return []
  const actions: PageAction[] = []
  if (canWrite.value && r.status === 'published') {
    actions.push({
      key: 'variation',
      label: t('recipes.variations.create'),
      icon: 'mdi mdi-source-branch-plus',
      command: () => void router.push({ name: 'recipe-variation-new', params: { id: r.id } }),
    })
  }
  if (canWrite.value && !isOwner.value) {
    actions.push({
      key: 'copy',
      label: t('recipes.copies.copy'),
      icon: 'mdi mdi-content-copy',
      busy: copying.value,
      disabled: copying.value,
      command: () => void copyAsMine(),
    })
  }
  if (!isMirror.value) {
    actions.push({
      key: 'export',
      label: t('recipes.detail.export'),
      icon: 'mdi mdi-file-export-outline',
      busy: exporting.value,
      disabled: exporting.value,
      command: () => void exportCui(),
    })
  }
  if (base.value?.can_edit) {
    actions.push({
      key: 'edit',
      label: t('common.edit'),
      icon: 'mdi mdi-pencil-outline',
      command: () => void router.push({ name: 'recipe-edit', params: { id: r.id } }),
    })
    if (isOwner.value) {
      actions.push({
        key: 'co-editors',
        label: t('recipes.coEditors.manage'),
        icon: 'mdi mdi-account-edit-outline',
        command: () => (coEditorsOpen.value = true),
      })
    }
  }
  if (base.value?.can_delete) {
    const draft = r.status === 'draft'
    actions.push({
      key: draft ? 'publish' : 'unpublish',
      label: draft ? t('recipes.detail.publish') : t('recipes.detail.unpublish'),
      icon: draft ? 'mdi mdi-earth' : 'mdi mdi-earth-off',
      command: () => void togglePublished(),
    })
    actions.push({
      key: 'delete',
      label: t('common.delete'),
      icon: 'mdi mdi-delete-outline',
      danger: true,
      command: () => (deleteOpen.value = true),
    })
  }
  return actions
})
function pageAction(item: MenuItem): PageAction {
  return item as PageAction
}

// Whether the step texts highlight what they mention, as the reader chose on
// their account page. Visitors and older accounts get the highlighting.
// A phone next to the stove stays readable while the recipe is open.
useKeepScreenOn()
const highlightMentions = computed(() => currentUser.user?.recipe_highlight_mentions ?? true)

// The cards below the recipe the reader chose to see on their account page.
const cards = computed(() => {
  const user = currentUser.user
  return {
    tips: user?.recipe_show_tips ?? true,
    notes: user?.recipe_show_notes ?? true,
    cooked: user?.recipe_show_cooked ?? true,
    rating: user?.recipe_show_rating ?? true,
  }
})
</script>

<template>
  <div v-if="recipe" class="recipe">
    <header class="recipe-hero" :class="{ 'recipe-hero--plain': !cover }">
      <div v-if="cover" class="recipe-cover">
        <img :src="cover" alt="" />
      </div>
      <div class="recipe-intro">
        <div class="recipe-badges screen-only">
          <Tag v-if="recipe.status === 'draft'" :value="t('recipes.status.draft')" severity="warn" />
          <Tag
            v-if="isCoEditor"
            :value="t('recipes.coEditors.badge')"
            icon="mdi mdi-account-edit-outline"
            severity="info"
            data-testid="co-editor-badge"
          />
          <button
            v-if="isMirror"
            type="button"
            class="recipe-badge-button"
            aria-haspopup="dialog"
            data-testid="mirror-badge"
            @click="mirrorInfoOpen = true"
          >
            <Tag :value="t('recipes.mirror.badge')" icon="mdi mdi-transit-connection-variant" severity="info" />
          </button>
        </div>
        <h1 class="recipe-title">{{ recipe.title }}</h1>
        <p v-if="variation" class="print-only recipe-print-variation" data-testid="print-variation">
          {{ t('recipes.print.variation', { name: variation.name }) }}
        </p>
        <ScrollFade v-if="recipe.description" class="recipe-description-box">
          <RichText class="recipe-description" :text="recipe.description" />
        </ScrollFade>
        <ul class="recipe-meta">
          <li v-if="recipe.total_minutes">
            <RecipeDuration :minutes="recipe.total_minutes" />
          </li>
          <li
            v-for="need in needs.filter((n) => n.sub_recipe.accessible && n.sub_recipe.total_minutes)"
            :key="`time-${need.sub_recipe.id}`"
          >
            {{ t('recipes.subRecipes.plus', { title: need.sub_recipe.title }) }}
            <RecipeDuration :minutes="need.sub_recipe.total_minutes!" :icon="false" />
          </li>
          <li>
            <span class="mdi mdi-chef-hat" aria-hidden="true" />
            {{ t(`recipes.difficulty.${recipe.difficulty}`) }}
          </li>
          <li v-if="recipe.rating_average !== null" class="screen-only">
            <span class="mdi mdi-star recipe-star" aria-hidden="true" />
            {{ t('recipes.card.rating', { avg: recipe.rating_average.toFixed(1), count: recipe.rating_count }) }}
          </li>
          <li v-if="seasonText" :title="t('recipes.detail.seasonHint')">
            <span class="mdi mdi-sprout-outline" aria-hidden="true" />
            {{ t('recipes.detail.season') }}: {{ seasonText }}
            <Tag v-if="recipe.in_season" :value="t('recipes.detail.seasonNow')" severity="success" />
          </li>
          <li v-if="recipe.owner">
            <UserAvatar class="owner-avatar" :name="recipe.owner.display_name" :avatar-id="recipe.owner.avatar_id" />
            {{ t('recipes.detail.by', { name: recipe.owner.display_name }) }}
          </li>
          <li v-else-if="attribution" data-testid="mirror-attribution">
            <UserAvatar
              v-if="mirrorAuthor?.author_name"
              class="owner-avatar"
              :name="mirrorAuthor.author_name"
              :avatar-id="mirrorAuthor.author_avatar_id"
            />
            <span v-else class="mdi mdi-account-outline" aria-hidden="true" />
            {{ attribution }}
          </li>
          <li v-if="coEditors.length">
            <span class="mdi mdi-account-edit-outline" aria-hidden="true" />
            {{ t('recipes.coEditors.list', { names: coEditors.map((p) => p.display_name).join(', ') }) }}
          </li>
        </ul>
        <p v-if="base?.based_on" class="recipe-lineage screen-only" data-testid="recipe-based-on">
          <span class="mdi mdi-content-copy" aria-hidden="true" />
          <RouterLink
            v-if="base.based_on.recipe.accessible && base.based_on.recipe.id"
            :to="{ name: 'recipe', params: { id: base.based_on.recipe.id } }"
          >
            {{
              base.based_on.owner
                ? t('recipes.copies.basedOnBy', { title: base.based_on.recipe.title, name: base.based_on.owner.display_name })
                : t('recipes.copies.basedOn', { title: base.based_on.recipe.title })
            }}
          </RouterLink>
          <template v-else>{{ t('recipes.copies.basedOnHidden') }}</template>
        </p>
        <div v-if="base && base.based_on_count > 0" class="recipe-lineage screen-only">
          <button type="button" class="recipe-lineage-toggle" :aria-expanded="!!copies" @click="showCopies">
            <span class="mdi mdi-source-fork" aria-hidden="true" />
            {{ t('recipes.copies.count', { n: base.based_on_count }, base.based_on_count) }}
          </button>
          <ul v-if="copies" class="recipe-copies">
            <li v-for="copy in copies" :key="copy.recipe.id">
              <RouterLink :to="{ name: 'recipe', params: { id: copy.recipe.id } }">{{ copy.recipe.title }}</RouterLink>
              <span v-if="copy.owner" class="hint"> {{ t('recipes.copies.by', { name: copy.owner.display_name }) }}</span>
            </li>
          </ul>
        </div>
        <ul v-if="recipe.diets.length" class="recipe-diets" :aria-label="t('recipes.diets.fits')">
          <li v-for="diet in recipe.diets" :key="diet">
            <span class="mdi mdi-leaf" aria-hidden="true" />
            {{ t(`diets.${diet}`) }}
          </li>
        </ul>
        <p v-if="unknownMarkers.length" class="recipe-unknown" data-testid="unknown-markers">
          <span class="mdi mdi-help-circle-outline" aria-hidden="true" />
          {{ unknownMarkers.map((m) => t('recipes.mirror.unknownValue', { value: m })).join(', ') }}
        </p>
        <p v-if="unconfirmedNames.length" class="recipe-unknown" data-testid="unconfirmed-ingredients">
          <span class="mdi mdi-help-circle-outline" aria-hidden="true" />
          {{ t('recipes.diets.unconfirmed', { names: unconfirmedNames.join(', ') }) }}
        </p>
        <ul v-if="recipe.tags.length" class="recipe-tags screen-only">
          <li v-for="tag in recipe.tags" :key="tag.id">
            <RouterLink :to="{ name: 'recipes', query: { tag: tag.id } }">{{ tag.name }}</RouterLink>
          </li>
        </ul>
        <div class="recipe-actions screen-only">
          <RouterLink
            :to="{
              name: 'recipe-cook',
              params: { id: recipe.id },
              query: version ? { servings, variation: version } : { servings },
            }"
            custom
          >
            <template #default="{ navigate }">
              <Button
                :label="t('recipes.detail.cook')"
                icon="mdi mdi-play"
                class="recipe-cook-button"
                @click="navigate"
              />
            </template>
          </RouterLink>
          <Button
            :label="recipe.is_favourite ? t('recipes.detail.favourited') : t('recipes.detail.favourite')"
            :icon="recipe.is_favourite ? 'mdi mdi-heart' : 'mdi mdi-heart-outline'"
            severity="secondary"
            outlined
            data-testid="recipe-favourite"
            @click="toggleFavourite"
          />
          <Button
            :label="cookedToday ? t('recipes.cooked.today') : t('recipes.cooked.button')"
            :icon="cookedToday ? 'mdi mdi-check-circle' : 'mdi mdi-check-circle-outline'"
            severity="secondary"
            outlined
            data-testid="recipe-cooked"
            :disabled="cookedToday"
            @click="cookedOpen = true"
          />
          <Button
            :label="t('recipes.addToList.button')"
            icon="mdi mdi-cart-plus"
            severity="secondary"
            outlined
            @click="listOpen = true"
          />
          <Button
            :label="t('recipes.detail.print')"
            icon="mdi mdi-printer-outline"
            severity="secondary"
            outlined
            data-testid="recipe-print"
            @click="printRecipe"
          />
          <div v-if="pageActions.length" class="recipe-dial-slot">
            <SpeedDial
              :model="pageActions"
              direction="down"
              show-icon="mdi mdi-dots-vertical"
              hide-icon="mdi mdi-close"
              button-class="recipe-dial-toggle"
              :button-props="{ severity: 'secondary', outlined: true }"
              :aria-label="t('recipes.detail.moreActions')"
              class="recipe-dial"
              data-testid="recipe-dial"
            >
              <template #item="{ item, onClick }">
                <Button
                  v-tooltip.right="pageAction(item).label"
                  role="menuitem"
                  :tabindex="-1"
                  :severity="pageAction(item).danger ? 'danger' : 'secondary'"
                  :disabled="!!item.disabled"
                  rounded
                  class="recipe-dial-action"
                  :data-testid="`recipe-${pageAction(item).key}`"
                  @click="onClick"
                >
                  <span
                    :class="pageAction(item).busy ? 'mdi mdi-loading mdi-spin' : pageAction(item).icon"
                    aria-hidden="true"
                  />
                  <span class="visually-hidden">{{ pageAction(item).label }}</span>
                </Button>
              </template>
            </SpeedDial>
          </div>
        </div>
      </div>
    </header>


    <ContentCard
      v-if="variations.length"
      as="section"
      class="recipe-panel recipe-variations screen-only"
      data-testid="recipe-variations"
    >
      <VariationSwitch :model-value="version" :variations="variations" @update:model-value="chooseVersion" />
      <div v-if="variation" class="variation-info" data-testid="variation-info">
        <h2 class="variation-name">
          {{ variation.name }}
          <Tag v-if="variation.private" :value="t('recipes.variations.private')" icon="mdi mdi-lock-outline" severity="secondary" />
        </h2>
        <p class="hint">{{ variationBy(variation) }}</p>
        <p v-if="variation.note" class="variation-note">{{ variation.note }}</p>
        <p v-if="!variation.changes.length" class="hint">{{ t('recipes.variations.empty') }}</p>
        <div v-if="variation.is_stale" class="variation-stale" data-testid="variation-stale">
          <Message severity="warn">{{ t('recipes.variations.staleIntro') }}</Message>
          <div v-for="note in staleNotes" :key="note.step" class="variation-stale-step">
            <p class="variation-stale-head">
              <span class="mdi mdi-history" aria-hidden="true" />
              {{ t('recipes.detail.step', { n: note.step }) }}:
              {{ note.state === 'deleted' ? t('recipes.variations.staleDeleted') : t('recipes.variations.stale') }}
            </p>
            <p class="hint">{{ t('recipes.variations.staleWas') }}</p>
            <RichText class="variation-stale-text" :text="note.old_text" />
            <template v-if="note.state === 'deleted'">
              <VariationChangeSummary
                v-for="change in variation.changes.filter((c) => c.step === note.step)"
                :key="change.id"
                :change="change"
              />
            </template>
          </div>
        </div>
        <div class="row-actions variation-actions">
          <RouterLink
            v-if="variation.can_edit && !variation.mirrored"
            :to="{ name: 'recipe-variation-edit', params: { id: recipe.id, variationId: variation.id } }"
            custom
          >
            <template #default="{ navigate }">
              <Button :label="t('recipes.variations.edit')" icon="mdi mdi-pencil-outline" severity="secondary" text @click="navigate" />
            </template>
          </RouterLink>
          <Button
            v-if="variation.can_adopt && !isMirror && variation.changes.length"
            :label="t('recipes.variations.adopt')"
            icon="mdi mdi-call-merge"
            severity="secondary"
            outlined
            @click="adoptOpen = true"
          />
          <Button
            v-if="variation.can_delete && !variation.mirrored"
            :label="t('recipes.variations.delete')"
            icon="mdi mdi-delete-outline"
            severity="danger"
            text
            @click="confirmDeleteVariation(variation)"
          />
        </div>
      </div>
    </ContentCard>

    <WarningBanner v-if="recipe.warnings.length" class="screen-only" :warnings="recipe.warnings" />
    <Message v-if="guests.length && recipe.unsuitable_for_guests" class="screen-only" severity="warn">
      <span class="mdi mdi-account-alert-outline" aria-hidden="true" />
      <strong>{{ t('recipes.guests.flag') }}</strong>
      {{ t('recipes.guests.pageHint', guests.length) }}
      <template v-if="unknownAllergens.length || unknownMarkers.length">
        <br />
        <span data-testid="guests-might-not-fit">{{ t('recipes.mirror.guestsMightNotFit') }}</span>
      </template>
    </Message>
    <Message v-else-if="guests.length" class="screen-only" severity="success">
      <span class="mdi mdi-account-check-outline" aria-hidden="true" />
      {{ t('recipes.guests.suits', guests.length) }}
    </Message>

    <div class="recipe-body">
      <aside class="recipe-side">
        <ContentCard as="section" v-if="needs.length" class="recipe-panel recipe-needs">
          <h2>{{ t('recipes.subRecipes.needs') }}</h2>
          <ul class="needs">
            <li v-for="(need, i) in needs" :key="need.sub_recipe.id ?? `hidden-${i}`" class="need">
              <img
                v-if="need.sub_recipe.cover_image_id"
                :src="imageUrl(need.sub_recipe.cover_image_id)"
                alt=""
                class="need-thumb"
              />
              <span v-else class="need-thumb need-thumb--empty mdi mdi-book-open-page-variant-outline" aria-hidden="true" />
              <span class="need-text">
                <RouterLink
                  v-if="need.sub_recipe.accessible && need.sub_recipe.id"
                  :to="{ name: 'recipe', params: { id: need.sub_recipe.id } }"
                  class="need-title"
                >
                  {{ need.sub_recipe.title }}
                </RouterLink>
                <span v-else class="need-hidden">{{ t('recipes.subRecipes.hidden') }}</span>
                <span class="need-amount">{{ needAmount(need) }}</span>
              </span>
            </li>
          </ul>
        </ContentCard>
        <ContentCard as="section" class="recipe-panel">
          <div class="recipe-panel-head">
            <h2>{{ t('recipes.detail.ingredients') }}</h2>
            <ServingsStepper v-model="servings" class="screen-only" />
            <span class="print-only recipe-print-servings">
              {{ t('recipes.servings.count', { n: servings }, servings) }}
            </span>
          </div>
          <IngredientLines :items="ingredients" :warn-ids="warnIds" />
        </ContentCard>

        <ContentCard
          v-if="equipmentGroups.length || plainEquipment.length"
          as="section"
          class="recipe-panel"
          data-testid="recipe-equipment"
        >
          <h2>{{ t('recipes.equipment.title') }}</h2>
          <p v-if="missingCount" class="recipe-equipment-missing">
            <span class="mdi mdi-alert-circle-outline" aria-hidden="true" />
            {{ t('recipes.equipment.missingCount', missingCount) }}
          </p>
          <template v-for="(group, g) in equipmentGroups" :key="group.subRecipe?.id ?? `own-${g}`">
            <h3 v-if="group.subRecipe" class="recipe-equipment-group">
              <span class="mdi mdi-book-open-page-variant-outline" aria-hidden="true" />
              {{
                group.subRecipe.accessible
                  ? t('recipes.equipment.forSubRecipe', { title: group.subRecipe.title })
                  : t('recipes.equipment.forHidden')
              }}
            </h3>
            <EquipmentList :items="group.items" />
          </template>
          <EquipmentList v-if="plainEquipment.length" :items="plainEquipment" />
        </ContentCard>

        <ContentCard as="section" class="recipe-panel">
          <h2>{{ t('recipes.nutrition.title') }}</h2>
          <p class="hint">{{ t('recipes.nutrition.perServing') }}</p>
          <NutritionPanel :nutrition="recipe.nutrition" />
          <h3 class="recipe-allergens-title">{{ t('recipes.detail.allergens') }}</h3>
          <p v-if="recipe.allergens.length || unknownAllergens.length" class="recipe-allergens">
            {{
              [
                ...recipe.allergens.map((a) => t(`allergens.${a}`)),
                ...unknownAllergens.map((a) => t('recipes.mirror.unknownValue', { value: a })),
              ].join(', ')
            }}
          </p>
          <p v-else class="hint">{{ t('recipes.detail.noAllergens') }}</p>
          <p v-if="sourceAllergens.length" class="hint" data-testid="source-allergens">
            <span class="mdi mdi-information-outline" aria-hidden="true" />
            {{
              t('recipes.mirror.sourceAllergens', {
                instance: mirror?.instance_name ?? '',
                names: sourceAllergens.map((a) => t(`allergens.${a}`)).join(', '),
              })
            }}
          </p>
        </ContentCard>
      </aside>

      <div class="recipe-main">
        <ContentCard as="section" class="recipe-panel" data-testid="recipe-steps">
          <h2>{{ t('recipes.detail.steps') }}</h2>
          <ol class="steps">
            <li
              v-for="(step, s) in steps"
              :key="step.position"
              class="step"
              :class="{
                'step--added': markerAt(markers, step.position)?.added,
                'step--changed': markerAt(markers, step.position)?.changed,
              }"
            >
              <div class="step-number" aria-hidden="true">{{ step.position }}</div>
              <div class="step-content">
                <h3 class="visually-hidden">{{ t('recipes.detail.step', { n: step.position }) }}</h3>
                <p v-if="markerAt(markers, step.position)?.added" class="step-mark screen-only" data-testid="step-added">
                  <span class="mdi mdi-source-branch" aria-hidden="true" />
                  {{ t('recipes.variations.added') }}
                </p>
                <p
                  v-else-if="markerAt(markers, step.position)?.text_changed"
                  class="step-mark screen-only"
                  data-testid="step-changed"
                >
                  <span class="mdi mdi-source-branch" aria-hidden="true" />
                  {{ t('recipes.variations.changedText') }}
                </p>
                <div
                  v-if="step.shownLines.length || markerAt(markers, step.position)?.removed.length || step.equipment.length || step.plainEquipment.length"
                  class="step-needs"
                >
                  <div v-if="step.shownLines.length" class="step-ingredients">
                    <h4>{{ t('recipes.detail.stepIngredients') }}</h4>
                    <IngredientLines compact :items="step.shownLines" :warn-ids="warnIds" :marks="step.shownMarks" />
                  </div>
                  <div v-if="markerAt(markers, step.position)?.removed.length" class="step-removed screen-only">
                    <h4>{{ t('recipes.variations.leftOut') }}</h4>
                    <ul>
                      <li v-for="line in markerAt(markers, step.position)!.removed" :key="line.change_id">
                        <s>{{ line.sub_recipe?.title ?? line.name }}</s>
                      </li>
                    </ul>
                  </div>
                  <div v-if="step.equipment.length || step.plainEquipment.length" class="step-ingredients">
                    <h4>{{ t('recipes.equipment.stepTitle') }}</h4>
                    <EquipmentList :items="[...step.equipment, ...step.plainEquipment]" />
                  </div>
                </div>
                <RichText
                  class="step-text"
                  :class="{ 'step-text--changed': markerAt(markers, step.position)?.text_changed }"
                  :plain-mentions="!highlightMentions"
                  :text="step.text"
                  :resolve="
                    lineResolver(step.ingredients, {
                      hiddenName: t('recipes.subRecipes.hidden'),
                      equipment: step.equipment,
                    })
                  "
                />
                <p v-if="step.duration_minutes" class="step-duration">
                  <span class="mdi mdi-timer-outline" aria-hidden="true" />
                  <RecipeDuration :minutes="step.duration_minutes" :icon="false" />
                </p>
                <img
                  v-if="step.image_id"
                  :src="imageUrl(step.image_id, 'original')"
                  alt=""
                  class="step-image"
                  loading="lazy"
                />
                <details
                  v-for="difference in differences[s] ?? []"
                  :key="difference.variation.id"
                  class="step-differently screen-only"
                  data-testid="step-differently"
                >
                  <summary>
                    <span class="mdi mdi-source-branch" aria-hidden="true" />
                    {{
                      t('recipes.variations.doesDifferently', {
                        name: authorName(difference.variation) ?? t('recipes.variations.variationName', { name: difference.variation.name }),
                      })
                    }}
                  </summary>
                  <div class="step-differently-body">
                    <p class="hint">{{ difference.variation.name }}</p>
                    <VariationChangeSummary
                      v-for="change in difference.changes"
                      :key="change.id"
                      :change="change"
                      :stale="staleStep(difference.variation, change.step)"
                    />
                    <Button
                      :label="t('recipes.variations.showVariation')"
                      icon="mdi mdi-eye-outline"
                      size="small"
                      severity="secondary"
                      outlined
                      @click="chooseVersion(difference.variation.id)"
                    />
                  </div>
                </details>
              </div>
            </li>
          </ol>
        </ContentCard>

        <ContentCard as="section" v-if="cards.tips && recipe.tips"  class="recipe-panel" data-testid="recipe-card-tips">
          <h2>{{ t('recipes.detail.tips') }}</h2>
          <RichText class="recipe-tips" :text="recipe.tips" />
        </ContentCard>

        <ContentCard as="section" v-if="cards.notes" class="recipe-panel screen-only" data-testid="recipe-card-notes">
          <h2>{{ t('recipes.note.title') }}</h2>
          <NotePanel :recipe-id="recipe.id" :text="recipe.own_note" />
        </ContentCard>

        <ContentCard as="section" v-if="cards.cooked"  class="recipe-panel screen-only" data-testid="recipe-card-cooked">
          <div class="recipe-panel-head">
            <h2>{{ t('recipes.detail.cookedTitle') }}</h2>
            <SelectButton
              v-model="onlyMine"
              :options="[
                { value: false, label: t('recipes.detail.cookedEveryone') },
                { value: true, label: t('recipes.detail.cookedMine') },
              ]"
              option-label="label"
              option-value="value"
              :allow-empty="false"
              :aria-label="t('recipes.detail.cookedFilter')"
            />
          </div>
          <p v-if="recipe.last_cooked_by_me" class="hint">
            {{ t('recipes.detail.lastCookedByMe', { date: dateLabel(recipe.last_cooked_by_me) }) }}
          </p>
          <ul v-if="cookEvents.length" class="cooked-list">
            <li v-for="event in cookEvents" :key="event.id">
              <strong>{{ event.user?.display_name ?? '?' }}</strong>
              · {{ dateLabel(event.cooked_on) }}
              <span v-if="event.variation" class="cooked-variation">
                {{ t('recipes.variations.cookedVariation', { name: event.variation.name }) }}
              </span>
              <span v-if="event.note" class="cooked-note">„{{ event.note }}“</span>
            </li>
          </ul>
          <p v-else class="hint">{{ t('recipes.detail.neverCooked') }}</p>
          <div class="row-actions">
            <Button
              :label="cookedToday ? t('recipes.cooked.today') : t('recipes.cooked.button')"
              :icon="cookedToday ? 'mdi mdi-check-circle' : 'mdi mdi-check-circle-outline'"
              severity="secondary"
              outlined
              data-testid="recipe-cooked"
              :disabled="cookedToday"
              @click="cookedOpen = true"
            />
          </div>
        </ContentCard>

        <ContentCard as="section" v-if="cards.rating" class="recipe-panel screen-only" data-testid="recipe-card-rating">
          <h2>
            {{ variation ? t('recipes.variations.ratingTitle', { name: variation.name }) : t('recipes.rating.title') }}
          </h2>
          <RatingPanel
            :recipe-id="recipe.id"
            :average="recipe.rating_average"
            :count="recipe.rating_count"
            :own="recipe.own_rating"
            :variation-id="version"
            @changed="onRated"
          />
          <p
            v-if="variations.length && base && base.rating_overall_average !== null"
            class="hint"
            data-testid="rating-overall"
          >
            {{
              t(
                'recipes.variations.overall',
                { avg: base.rating_overall_average.toFixed(1), count: base.rating_overall_count },
                base.rating_overall_count,
              )
            }}
          </p>
        </ContentCard>

        <p v-if="recipe.source_url || recipe.source_name" class="recipe-source">
          {{ t('recipes.detail.source') }}:
          <a v-if="recipe.source_url" :href="recipe.source_url" target="_blank" rel="noopener noreferrer">
            {{ recipe.source_name || recipe.source_url }}
          </a>
          <template v-else>{{ recipe.source_name }}</template>
        </p>

        <RecipePrintQr :public-id="version ?? recipe.id" />
      </div>
    </div>

    <Dialog
      v-if="isMirror"
      v-model:visible="mirrorInfoOpen"
      modal
      :header="t('recipes.mirror.badge')"
      class="recipe-mirror-dialog"
    >
      <div class="recipe-mirror" data-testid="mirror-notice">
        <p>
          {{ t('recipes.mirror.notice', { instance: mirror?.instance_name ?? base?.mirror?.instance_name ?? '' }) }}
          <template v-if="canWrite">{{ t('recipes.mirror.copyHint') }}</template>
        </p>
        <a
          v-if="mirror?.source_url"
          :href="mirror.source_url"
          target="_blank"
          rel="noopener noreferrer"
          class="recipe-mirror-link"
          data-testid="mirror-source-link"
        >
          <span class="mdi mdi-open-in-new" aria-hidden="true" />
          {{ t('recipes.mirror.openAt', { instance: mirror.instance_name }) }}
        </a>
      </div>
    </Dialog>
    <DeleteRecipeDialog
      v-model:visible="deleteOpen"
      :recipe-id="recipe.id"
      :title="recipe.title"
      @deleted="onDeleted"
    />
    <AddToListDialog
      v-model:visible="listOpen"
      :recipe-id="recipe.id"
      :servings="servings"
      :needs="needs"
    />
    <CookedDialog
      v-model:visible="cookedOpen"
      :recipe-id="recipe.id"
      :servings="servings"
      :variation-id="version"
      @logged="onCooked"
    />
    <AdoptVariationDialog
      v-if="variation"
      v-model:visible="adoptOpen"
      :recipe-id="recipe.id"
      :variation="variation"
      @adopted="onAdopted"
    />
    <CoEditorsDialog
      v-if="isOwner"
      v-model:visible="coEditorsOpen"
      :recipe-id="recipe.id"
      @saved="(list) => (coEditors = list)"
    />
  </div>
  <ContentCard v-else-if="notFound">
    <EmptyState :message="t('recipes.detail.notFound')" icon="mdi mdi-book-off-outline">
      <RouterLink :to="{ name: 'recipes' }" custom>
        <template #default="{ navigate }">
          <Button :label="t('recipes.detail.backToRecipes')" severity="secondary" @click="navigate" />
        </template>
      </RouterLink>
    </EmptyState>
  </ContentCard>
  <div
    v-else-if="loading"
    class="recipe recipe-skeleton"
    role="status"
    :aria-label="t('recipes.loading')"
    data-testid="recipe-skeleton"
  >
    <div class="recipe-hero">
      <Skeleton class="recipe-cover" height="auto" />
      <div class="recipe-intro">
        <Skeleton class="recipe-title" width="75%" height="clamp(2.2rem, 8.8vw, 3.85rem)" />
        <Skeleton height="1.25rem" />
        <Skeleton width="60%" height="1.25rem" />
        <div class="recipe-meta">
          <Skeleton v-for="n in 3" :key="n" width="5.5rem" height="1.25rem" />
        </div>
        <div class="recipe-actions">
          <Skeleton class="recipe-cook-button" width="11rem" height="3rem" />
          <Skeleton v-for="n in 3" :key="n" width="8.5rem" height="2.5rem" />
        </div>
      </div>
    </div>
    <div class="recipe-body">
      <aside class="recipe-side">
        <ContentCard as="section" class="recipe-panel">
          <div class="recipe-panel-head">
            <Skeleton width="45%" height="1.875rem" />
            <Skeleton width="8rem" height="2.5rem" />
          </div>
          <div v-for="n in 6" :key="n" class="recipe-skeleton-line">
            <Skeleton width="3.5rem" height="1rem" />
            <Skeleton :width="`${45 + ((n * 17) % 35)}%`" height="1rem" />
          </div>
        </ContentCard>
        <ContentCard as="section" class="recipe-panel">
          <Skeleton width="50%" height="1.875rem" />
          <Skeleton v-for="n in 4" :key="n" :width="n % 2 ? '100%' : '80%'" height="1rem" />
        </ContentCard>
      </aside>
      <div class="recipe-main">
        <ContentCard as="section" class="recipe-panel">
          <Skeleton width="40%" height="1.875rem" />
          <ol class="steps">
            <li v-for="n in 3" :key="n" class="step">
              <Skeleton shape="circle" size="2.5rem" />
              <div class="step-content">
                <Skeleton height="1.25rem" />
                <Skeleton height="1.25rem" />
                <Skeleton :width="`${40 + n * 12}%`" height="1.25rem" />
                <Skeleton class="recipe-skeleton-step-lines" height="4rem" />
              </div>
            </li>
          </ol>
        </ContentCard>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.recipe {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

// Phone first: the cover runs edge to edge above the title, pulled over the
// page padding.
.recipe-hero {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.recipe-cover {
  margin: calc(-1 * var(--space-3)) calc(-1 * var(--space-3)) 0;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: var(--p-surface-100);

  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.p-dark .recipe-cover {
  background: var(--p-surface-800);
}

.recipe-intro {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

// Without a photo there is no empty frame: the intro becomes a full-width
// panel on the card surface, and the description keeps a comfortable line
// length.
.recipe-hero--plain .recipe-intro {
  padding: var(--space-5);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-surface-0);
}

.p-dark .recipe-hero--plain .recipe-intro {
  background: var(--p-surface-900);
}

.recipe-hero--plain .recipe-description {
  max-width: 70ch;
}

.recipe-badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);

  &:empty {
    display: none;
  }
}

.recipe-title {
  margin-bottom: var(--space-2);
  font-size: clamp(2rem, 8vw, 3.5rem);
  line-height: 1.1;
}

.recipe-description {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-lg);
}

.recipe-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-5);
  // Clear of the description above, so the facts read as their own row.
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
  color: var(--p-text-muted-color);

  // Each hint keeps its icon close to its own text; the wider gap above
  // separates the hints from each other.
  > li {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-1);
  }
}

.owner-avatar {
  --avatar-size: 1.5rem;

  display: inline-grid;
  vertical-align: middle;
}

.recipe-equipment-missing {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
  color: var(--p-orange-600);
  font-weight: 700;
}

.p-dark .recipe-equipment-missing {
  color: var(--p-orange-400);
}

.recipe-equipment-group {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin: var(--space-3) 0 var(--space-1);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.needs {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.need {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 3.25rem;
}

.need-thumb {
  flex: 0 0 3rem;
  width: 3rem;
  height: 3rem;
  border-radius: var(--p-border-radius-md);
  object-fit: cover;
}

.need-thumb--empty {
  display: grid;
  place-items: center;
  background: var(--p-surface-100);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xl);
}

.p-dark .need-thumb--empty {
  background: var(--p-surface-800);
}

.need-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.need-title {
  color: var(--p-primary-color);
  font-weight: 700;
}

.need-hidden {
  color: var(--p-text-muted-color);
  font-style: italic;
}

.need-amount {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.recipe-star {
  color: var(--p-yellow-500);
}

.recipe-diets {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--p-green-700);
  font-weight: 700;
}

.p-dark .recipe-diets {
  color: var(--p-green-400);
}

.recipe-unknown {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

// The badge of a mirror opens a dialog explaining where the recipe comes
// from, so the button only adds the pointer and a focus ring to the tag.
.recipe-badge-button {
  padding: 0;
  border: none;
  border-radius: var(--p-border-radius-sm);
  background: none;
  cursor: pointer;

  &:focus-visible {
    outline: 2px solid var(--p-primary-color);
    outline-offset: 2px;
  }
}

.recipe-mirror-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.recipe-mirror {
  display: grid;
  gap: var(--space-2);

  p {
    margin: 0;
  }
}

.recipe-mirror-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-1);
  font-weight: 700;
}

.recipe-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;

  a {
    display: inline-flex;
    align-items: center;
    min-height: 2rem;
    padding: 0 var(--space-3);
    border-radius: 2rem;
    background: var(--p-surface-100);
    color: inherit;
    text-decoration: none;
    font-size: var(--font-size-sm);
  }
}

.p-dark .recipe-tags a {
  background: var(--p-surface-800);
}

.recipe-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);

  // Every button of the bar, the dial's toggle included, shares one height.
  :deep(button) {
    height: 3rem;
  }
}

.recipe-cook-button {
  flex: 1 1 100%;
  font-size: var(--font-size-lg);
}

.recipe-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.recipe-side,
.recipe-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}

.recipe-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: auto;

  h2 {
    font-size: var(--font-size-2xl);
  }
}

.recipe-panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.recipe-allergens-title {
  margin-top: var(--space-2);
}

.steps {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  margin: 0;
  padding: 0;
  list-style: none;
}

.step {
  display: grid;
  grid-template-columns: 2.5rem 1fr;
  gap: var(--space-3);
}

.step-number {
  display: grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  font-weight: 800;
  font-size: var(--font-size-lg);
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.step-text {
  font-size: var(--font-size-lg);
  line-height: 1.55;
}

.step-duration {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-text-muted-color);
}

.step-image {
  width: 100%;
  max-width: 32rem;
  border-radius: var(--p-border-radius-md);
}

// What the step needs comes before what to do: its ingredients and its
// equipment side by side where there is room, each box only as wide as
// its content needs.
.step-needs {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--space-2);
}

.step-ingredients {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 100%;
  padding: var(--space-2) var(--space-3);
  border-left: 3px solid var(--p-primary-color);
  background: var(--p-surface-50);
  border-radius: 0 var(--p-border-radius-md) var(--p-border-radius-md) 0;

  h4 {
    color: var(--p-text-muted-color);
    font-size: var(--font-size-sm);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
}

.p-dark .step-ingredients {
  background: var(--p-surface-900);
}

.cooked-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.cooked-note {
  display: block;
  color: var(--p-text-muted-color);
  font-style: italic;
}

.recipe-source {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
  overflow-wrap: anywhere;
}

.recipe-lineage {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-text-muted-color);

  a {
    color: var(--p-primary-color);
    font-weight: 700;
  }
}

.recipe-lineage-toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 2.75rem;
  padding: 0;
  border: none;
  background: none;
  color: var(--p-primary-color);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.recipe-copies {
  flex-basis: 100%;
  margin: 0;
  padding-left: var(--space-5);
}

.recipe-variations {
  gap: var(--space-3);
}

.variation-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.recipe-panel .variation-name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-head);
  font-size: var(--font-size-xl);
  font-weight: 800;
}

.variation-note {
  font-style: italic;
}

.variation-stale {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.variation-stale-step {
  padding: var(--space-2) var(--space-3);
  border-left: 3px solid var(--p-orange-400);
}

.variation-stale-head {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-weight: 700;
}

.variation-stale-text {
  color: var(--p-text-muted-color);
}

.variation-actions {
  justify-content: flex-start;
}

.step--added .step-number,
.step--changed .step-number {
  outline: 3px solid var(--p-primary-200);
  outline-offset: 2px;
}

.step-mark {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-primary-color);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.step-text--changed {
  padding-left: var(--space-2);
  border-left: 3px solid var(--p-primary-color);
}

.step-removed {
  padding: var(--space-2) var(--space-3);
  color: var(--p-text-muted-color);

  h4 {
    font-size: var(--font-size-sm);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  ul {
    margin: 0;
    padding-left: var(--space-4);
  }
}

.step-differently {
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);

  summary {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    min-height: 2.75rem;
    padding: 0 var(--space-3);
    color: var(--p-primary-color);
    font-weight: 700;
    cursor: pointer;
  }
}

.step-differently-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  padding: 0 var(--space-3) var(--space-3);
}

.cooked-variation {
  color: var(--p-text-muted-color);
  font-style: italic;
}

.recipe-skeleton-line {
  display: flex;
  gap: var(--space-3);
}

.recipe-skeleton-step-lines {
  max-width: 32rem;
}

// The speed dial is the last button of the action bar and opens downwards
// over the page. SpeedDial renders several root nodes, so the scoped styles
// reach it through the slot this view owns. The closed dial lets clicks
// through everywhere but its own button.
.recipe-dial-slot {
  position: relative;
  z-index: 5;

  :deep(.recipe-dial) {
    pointer-events: none;
  }

  :deep(.recipe-dial-toggle) {
    width: 3rem;
    pointer-events: auto;
  }

  :deep(.recipe-dial [role='menu']) {
    position: absolute;
    top: 100%;
    left: 50%;
    padding-top: var(--space-2);
    transform: translateX(-50%);
  }
}

.recipe-dial-action {
  justify-content: center;
  width: 3rem;
  height: 3rem;
  padding: 0;
  box-shadow: var(--p-overlay-popover-shadow);
}

@media (min-width: $bp-sm) {
  .recipe-cover {
    margin: 0;
    border-radius: var(--p-border-radius-lg);
  }

  .recipe-cook-button {
    flex: 0 0 auto;
  }
}

// From a laptop up the cover sits beside the intro, and the ingredients stay
// in view beside the steps while the reader scrolls.
@media (min-width: $bp-lg) {
  // The intro is exactly as tall as the cover: `contain: size` keeps its
  // content from growing the row, a long description scrolls inside its
  // fading box, and the buttons sit at the cover's lower edge.
  .recipe-hero {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
    align-items: stretch;
    gap: var(--space-6);
  }

  .recipe-intro {
    contain: size;
  }

  .recipe-description-box {
    flex: 0 1 auto;
    min-height: 3lh;
  }

  .recipe-actions {
    margin-top: auto;
  }

  // Without a cover there is no height to match: the panel spans the page
  // and grows with its content.
  .recipe-hero--plain {
    grid-template-columns: minmax(0, 1fr);
  }

  .recipe-hero--plain .recipe-intro {
    contain: none;
    padding: var(--space-6);
  }

  // The columns sit as close together as the cards stacked in them.
  .recipe-body {
    display: grid;
    grid-template-columns: minmax(20rem, 1fr) minmax(0, 2fr);
    align-items: start;
    gap: var(--space-4);
  }

  .recipe-side {
    position: sticky;
    top: 0;
  }
}

.print-only {
  display: none;
}

// On paper the page is the recipe alone, in dark ink on white whatever the
// theme: no controls, no variation chrome, none of the reader's own layer,
// and the QR code at its foot. The ingredients sit beside the steps as on a
// laptop, and the cover is a small picture beside the title.
@media print {
  .recipe {
    --p-text-color: #000;
    --p-text-muted-color: #444;
    --p-content-border-color: #ccc;
    --p-surface-50: #fff;
    --p-surface-100: #f2f2f2;
    --p-surface-800: #f2f2f2;
    --p-surface-900: #fff;
    --p-surface-950: #fff;

    gap: var(--space-3);
    background: var(--paper);
    color: var(--p-text-color);
  }

  .screen-only {
    display: none;
  }

  .print-only {
    display: block;
  }

  .recipe-print-servings {
    display: inline;
    font-weight: 700;
  }

  .recipe-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 30%;
    align-items: start;
    gap: var(--space-4);
  }

  .recipe-cover {
    grid-column: 2;
    grid-row: 1;
    margin: 0;
    border-radius: var(--p-border-radius-md);
    break-inside: avoid;
  }

  .recipe-intro {
    grid-column: 1;
    grid-row: 1;
  }

  .recipe-hero--plain .recipe-intro,
  .p-dark .recipe-hero--plain .recipe-intro {
    padding: 0;
    border: 0;
    background: none;
  }

  .recipe-title {
    font-size: var(--font-size-4xl);
  }

  .recipe-description {
    font-size: var(--font-size-md);
  }

  // The paper shows the whole description, never a scrolled box.
  .recipe-intro {
    contain: none;
  }

  .recipe-description-box {
    overflow: visible;
    mask-image: none;
  }

  .recipe-body {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
    align-items: start;
    gap: var(--space-5);
  }

  .recipe-side {
    position: static;
  }

  .recipe-panel {
    padding: 0;
    border: none;
    box-shadow: none;
    background: none;

    h2 {
      font-size: var(--font-size-xl);
    }
  }

  .need-thumb {
    display: none;
  }

  .steps {
    gap: var(--space-3);
  }

  .step {
    break-inside: avoid;
    grid-template-columns: 1.75rem 1fr;
  }

  .step-number {
    width: 1.75rem;
    height: 1.75rem;
    border: 1px solid var(--p-text-color);
    background: none;
    color: var(--p-text-color);
    font-size: var(--font-size-md);
  }

  .step--added .step-number,
  .step--changed .step-number {
    outline: none;
  }

  .step-text {
    font-size: var(--font-size-md);
  }

  .step-text--changed {
    padding-left: 0;
    border-left: none;
  }

  .step-image {
    max-width: 6cm;
    max-height: 4cm;
    object-fit: cover;
  }

  .step-ingredients {
    padding: var(--space-1) var(--space-2);
    border-left-color: var(--p-content-border-color);
  }

  .recipe-source a {
    color: inherit;
  }
}
</style>
