<script setup lang="ts">
/**
 * Cook mode: the recipe one step at a time, full screen, in big type, with
 * that step's ingredients scaled to the servings chosen on the recipe page.
 * Swipe, the arrow keys or the buttons move between steps; a step with a
 * duration offers a timer; the screen stays on while cooking, unless the
 * reader turned that off on the account page. A start
 * screen lists the sub-recipes to make first and the equipment to set out,
 * marking what the kitchen lacks. The last screen logs the meal. A recipe
 * with variations first asks which version to cook, unless the link says,
 * and cooks the chosen variation as the backend applies it.
 */
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { onKeyStroke, useSwipe } from '@vueuse/core'

import { useAppToast } from '@/core/composables/useAppToast'
import {
  getRecipe,
  listVariations,
  viewVariation,
  type RecipeDetailResponse,
  type StepMarkerView,
  type VariationResponse,
} from '@/features/recipes/api/recipes'
import CookedDialog from '@/features/recipes/components/CookedDialog.vue'
import EquipmentList from '@/features/recipes/components/EquipmentList.vue'
import IngredientLines from '@/features/recipes/components/IngredientLines.vue'
import ServingsStepper from '@/features/recipes/components/ServingsStepper.vue'
import { useAmountFormat } from '@/features/recipes/composables/useAmountFormat'
import { useCookMode, useStepTimer } from '@/features/recipes/composables/useCookMode'
import { scaleFactor, scaleIngredients } from '@/features/recipes/utils/scaling'
import { lineResolver } from '@/features/recipes/utils/mentionResolver'
import { setOutList } from '@/features/recipes/utils/equipment'
import { extraIngredients, mergeStepLines, plainEquipmentOf } from '@/features/recipes/utils/mirrors'
import { ORIGINAL, authorName, cookVersion, lineMarks, markerAt } from '@/features/recipes/utils/variations'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import EmptyState from '@/shared/components/EmptyState.vue'
import { imageUrl } from '@/shared/components/recipes/recipeImage'
import RichText from '@/shared/components/richText/RichText.vue'
import { useKeepScreenOn } from '@/shared/composables/useKeepScreenOn'

const { t, locale } = useI18n()
const { style: amountStyle } = useAmountFormat()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()

const recipe = ref<RecipeDetailResponse | null>(null)
const failed = ref(false)
// The versions on offer, the one being cooked (null for the original), and
// whether the cook still has to choose.
const variations = ref<VariationResponse[]>([])
const variationId = ref<string | null>(null)
const askVersion = ref(false)
const markers = ref<StepMarkerView[]>([])
const cooking = computed(() => variations.value.find((v) => v.id === variationId.value) ?? null)
const servings = ref(Number(route.query.servings) || 0)
// The sub-recipes to make first and the equipment to set out, shown before
// step 1. A sub-recipe opened from here comes back to this screen.
const showIntro = ref(false)
const parentId = computed(() =>
  typeof route.query.parent === 'string' ? route.query.parent : null,
)
const firstNeeds = computed(() =>
  (recipe.value?.needs ?? []).map((need) => ({
    ...need,
    batches: need.batches * factor.value,
  })),
)
const setOut = computed(() => setOutList(recipe.value?.equipment ?? []))
// The kitchen's gaps for the current step, from the "You'll need" list.
const missingIds = computed(
  () => new Set(setOut.value.filter((n) => n.missing === true).map((n) => n.equipment.id)),
)
// A mirror's lines kept as text, put back into the step they belong to:
// the step itself on the original, the step a variation's step came from.
const mirror = computed(() => recipe.value?.mirror_details ?? null)
const sourceIndex = computed(() => {
  if (!step.value) return null
  if (!variationId.value) return index.value
  const origin = markerAt(markers.value, step.value.position)?.origin_step
  return origin ? origin - 1 : null
})
const stepEquipment = computed(() => [
  ...(step.value?.equipment ?? []).map((item) => ({ ...item, missing: missingIds.value.has(item.equipment.id) })),
  ...plainEquipmentOf(mirror.value, sourceIndex.value),
])
const showAll = ref(false)
const cookedOpen = ref(false)
const logged = ref(false)

const stepCount = computed(() => recipe.value?.steps.length ?? 0)
const { index, isFirst, isFinish, progress, next, prev, goTo } = useCookMode(stepCount)

const factor = computed(() =>
  recipe.value ? scaleFactor(servings.value, recipe.value.base_servings) : 1,
)
const step = computed(() => recipe.value?.steps[index.value] ?? null)
const stepLines = computed(() =>
  step.value
    ? mergeStepLines(
        step.value.ingredients,
        mirror.value,
        sourceIndex.value,
        lineMarks(markerAt(markers.value, step.value.position), step.value.ingredients.length),
      )
    : { items: [], marks: [] },
)
const stepIngredients = computed(() => scaleIngredients(stepLines.value.items, factor.value))
const stepMarks = computed(() => stepLines.value.marks)
const allIngredients = computed(() =>
  recipe.value
    ? scaleIngredients([...recipe.value.ingredients, ...extraIngredients(mirror.value)], factor.value)
    : [],
)

// One timer for the whole session, so moving on while something simmers
// keeps it counting; the chip at the bottom names the step it belongs to.
const timerStep = ref<number | null>(null)
const timer = useStepTimer(() => {
  toast.success(t('recipes.cookMode.timerDone'))
  if ('vibrate' in navigator) navigator.vibrate([300, 150, 300])
  beep()
  timerStep.value = null
})

function beep() {
  try {
    const audio = new AudioContext()
    const osc = audio.createOscillator()
    osc.frequency.value = 880
    osc.connect(audio.destination)
    osc.start()
    osc.stop(audio.currentTime + 0.4)
  } catch {
    // No audio output: the toast and the vibration still tell the cook.
  }
}

function startTimer() {
  if (!step.value?.duration_minutes) return
  timerStep.value = index.value
  timer.start(step.value.duration_minutes)
}

const timerLabel = computed(() => {
  const s = timer.remaining.value
  const mm = String(Math.floor(s / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${mm}:${ss}`
})

useKeepScreenOn()

async function load() {
  try {
    const id = String(route.params.id)
    const [original, found] = await Promise.all([getRecipe(id), listVariations(id).catch(() => [])])
    variations.value = found
    const decision = cookVersion(route.query.variation, found)
    askVersion.value = decision.ask
    await applyVersion(original, decision.chosen)
  } catch (err) {
    failed.value = true
    toast.error(err)
  }
}

// Puts the chosen version on the stage: the original as read, or the
// variation as the backend applies it.
async function applyVersion(original: RecipeDetailResponse, chosen: string | null) {
  let next = original
  markers.value = []
  if (chosen) {
    const view = await viewVariation(original.id, chosen)
    next = view.recipe
    markers.value = view.steps
  }
  variationId.value = chosen
  recipe.value = next
  // Opened as a sub-recipe: as many servings as the batches the parent needs.
  const batches = Number(route.query.batches)
  if (batches > 0) servings.value = Math.max(1, Math.round(batches * next.base_servings))
  if (!servings.value) servings.value = next.base_servings
  showIntro.value = next.needs.length > 0 || next.equipment.length > 0
  goTo(0)
}

async function chooseVersion(chosen: string | null) {
  if (!recipe.value) return
  askVersion.value = false
  void router.replace({ query: { ...route.query, variation: chosen ?? ORIGINAL } })
  try {
    // The stage holds the original until a variation was chosen.
    await applyVersion(recipe.value, chosen)
  } catch (err) {
    toast.error(err)
  }
}

function cookFirst(subRecipeId: string, batches: number) {
  void router.push({
    name: 'recipe-cook',
    params: { id: subRecipeId },
    query: { batches: String(Math.round(batches * 100) / 100), parent: String(route.params.id) },
  })
}

function backToParent() {
  if (window.history.state?.back) router.back()
  else if (parentId.value) void router.push({ name: 'recipe-cook', params: { id: parentId.value } })
}

// Moving between a recipe and its sub-recipe reuses this view, so a new id
// starts over.
watch(
  () => route.params.id,
  (next, previous) => {
    if (next === previous) return
    recipe.value = null
    failed.value = false
    logged.value = false
    variations.value = []
    variationId.value = null
    askVersion.value = false
    markers.value = []
    servings.value = Number(route.query.servings) || 0
    goTo(0)
    void load()
  },
)

function close() {
  if (window.history.state?.back) router.back()
  else void router.push({ name: 'recipe', params: { id: String(route.params.id) } })
}

const stage = useTemplateRef<HTMLElement>('stage')
const { direction } = useSwipe(stage, {
  threshold: 60,
  onSwipeEnd: () => {
    if (direction.value === 'left') forward()
    else if (direction.value === 'right') prev()
  },
})

// From the make-this-first screen, forward leads to step 1.
function forward() {
  if (askVersion.value) return
  if (showIntro.value) showIntro.value = false
  else next()
}

onKeyStroke(['ArrowRight', 'PageDown'], (e) => {
  if (cookedOpen.value) return
  e.preventDefault()
  forward()
})
onKeyStroke(['ArrowLeft', 'PageUp'], (e) => {
  if (cookedOpen.value) return
  e.preventDefault()
  prev()
})

onMounted(() => {
  void load()
})

onBeforeUnmount(() => {
  timer.stop()
})
</script>

<template>
  <div class="cook-mode">
    <header class="cook-header">
      <Button
        icon="mdi mdi-close"
        text
        rounded
        severity="secondary"
        :aria-label="t('recipes.cookMode.close')"
        @click="close"
      />
      <div class="cook-header-title">
        <p class="cook-recipe-title">{{ recipe?.title ?? t('recipes.cookMode.title') }}</p>
        <p v-if="cooking" class="cook-progress-label" data-testid="cook-version">
          <span class="mdi mdi-source-branch" aria-hidden="true" />
          {{ cooking.name }}
        </p>
        <p v-if="recipe && !isFinish && !askVersion" class="cook-progress-label">
          {{ t('recipes.cookMode.step', { n: index + 1, total: stepCount }) }}
        </p>
      </div>
      <Button
        icon="mdi mdi-format-list-bulleted"
        text
        rounded
        severity="secondary"
        :aria-label="t('recipes.cookMode.allIngredients')"
        :aria-pressed="showAll"
        @click="showAll = !showAll"
      />
    </header>
    <ProgressBar
      :value="Math.round(progress * 100)"
      :show-value="false"
      class="cook-progress"
      :aria-label="t('recipes.cookMode.progress')"
    />

    <div v-if="recipe" ref="stage" class="cook-stage" aria-live="polite">
      <section v-if="askVersion" class="cook-screen" data-testid="cook-choose">
        <h1 class="cook-heading">{{ t('recipes.cookMode.chooseTitle') }}</h1>
        <p class="cook-finish-text">{{ t('recipes.cookMode.chooseText') }}</p>
        <ul class="cook-versions">
          <li>
            <button type="button" class="cook-version" data-testid="cook-choose-original" @click="chooseVersion(null)">
              <span class="cook-version-name">{{ t('recipes.variations.original') }}</span>
            </button>
          </li>
          <li v-for="variation in variations" :key="variation.id">
            <button
              type="button"
              class="cook-version"
              :data-testid="`cook-choose-${variation.id}`"
              @click="chooseVersion(variation.id)"
            >
              <span class="cook-version-name">
                <span class="mdi mdi-source-branch" aria-hidden="true" />
                {{ variation.name }}
              </span>
              <span class="cook-version-meta">
                {{ t('recipes.variations.by', { name: authorName(variation) ?? t('recipes.variations.formerMember') }) }}
              </span>
              <span v-if="variation.note" class="cook-version-meta">{{ variation.note }}</span>
            </button>
          </li>
        </ul>
      </section>

      <section v-else-if="showIntro && !showAll" class="cook-screen">
        <h1 class="cook-heading">
          {{ firstNeeds.length ? t('recipes.cookMode.firstTitle') : t('recipes.cookMode.setOutTitle') }}
        </h1>
        <p v-if="firstNeeds.length" class="cook-finish-text">{{ t('recipes.cookMode.firstText') }}</p>
        <ul v-if="firstNeeds.length" class="cook-first">
          <li v-for="(need, i) in firstNeeds" :key="need.sub_recipe.id ?? `hidden-${i}`" class="cook-first-item">
            <span class="cook-first-title">
              {{ need.sub_recipe.accessible ? need.sub_recipe.title : t('recipes.subRecipes.hidden') }}
            </span>
            <Button
              v-if="need.sub_recipe.accessible && need.sub_recipe.id"
              :label="t('recipes.cookMode.cookFirst')"
              icon="mdi mdi-play"
              severity="secondary"
              outlined
              @click="cookFirst(need.sub_recipe.id, need.batches)"
            />
          </li>
        </ul>
        <div v-if="setOut.length" class="cook-ingredients" data-testid="cook-set-out">
          <h2>{{ t('recipes.cookMode.setOut') }}</h2>
          <EquipmentList :items="setOut" large />
        </div>
        <Button
          :label="t('recipes.cookMode.startSteps')"
          icon="mdi mdi-chevron-right"
          icon-pos="right"
          size="large"
          @click="showIntro = false"
        />
      </section>

      <section v-else-if="showAll" class="cook-screen">
        <h1 class="cook-heading">{{ t('recipes.cookMode.allIngredients') }}</h1>
        <ServingsStepper v-model="servings" />
        <IngredientLines :items="allIngredients" large />
        <Button
          :label="t('recipes.cookMode.backToStep')"
          severity="secondary"
          outlined
          @click="showAll = false"
        />
      </section>

      <section v-else-if="step && !isFinish" :key="index" class="cook-screen">
        <div class="cook-step-number" aria-hidden="true">{{ index + 1 }}</div>
        <RichText
          class="cook-step-text"
          :text="step.text"
          :resolve="
            lineResolver(stepIngredients, {
              amounts: true,
              locale: contentLocaleOf(locale),
              amountStyle,
              hiddenName: t('recipes.subRecipes.hidden'),
              equipment: step.equipment,
            })
          "
        />
        <img v-if="step.image_id" :src="imageUrl(step.image_id, 'original')" alt="" class="cook-image" />
        <div v-if="step.duration_minutes" class="cook-timer-start">
          <Button
            v-if="timerStep !== index"
            :label="t('recipes.cookMode.startTimer', { m: step.duration_minutes })"
            icon="mdi mdi-timer-outline"
            severity="secondary"
            outlined
            size="large"
            @click="startTimer"
          />
        </div>
        <div v-if="stepIngredients.length" class="cook-ingredients">
          <h2>{{ t('recipes.cookMode.ingredients') }}</h2>
          <IngredientLines :items="stepIngredients" :marks="stepMarks" large />
        </div>
        <div v-if="stepEquipment.length" class="cook-ingredients" data-testid="cook-step-equipment">
          <h2>{{ t('recipes.cookMode.equipment') }}</h2>
          <EquipmentList :items="stepEquipment" large />
        </div>
      </section>

      <section v-else class="cook-screen cook-finish">
        <span class="mdi mdi-party-popper cook-finish-icon" aria-hidden="true" />
        <h1 class="cook-heading">{{ t('recipes.cookMode.doneTitle') }}</h1>
        <p class="cook-finish-text">{{ t('recipes.cookMode.doneText') }}</p>
        <Button
          v-if="!logged"
          :label="t('recipes.cooked.button')"
          icon="mdi mdi-check-circle-outline"
          size="large"
          @click="cookedOpen = true"
        />
        <p v-else class="cook-logged">
          <span class="mdi mdi-check-circle" aria-hidden="true" />
          {{ t('recipes.cooked.saved') }}
        </p>
        <Button
          v-if="parentId"
          :label="t('recipes.cookMode.backToParent')"
          icon="mdi mdi-arrow-left"
          size="large"
          @click="backToParent"
        />
        <Button :label="t('recipes.cookMode.backToRecipe')" severity="secondary" text @click="close" />
      </section>
    </div>
    <div v-else-if="failed" class="cook-stage">
      <EmptyState :message="t('recipes.detail.notFound')" icon="mdi mdi-book-off-outline" />
    </div>

    <div v-if="timer.running.value || timer.remaining.value > 0" class="cook-timer" role="timer">
      <span class="mdi mdi-timer-sand" aria-hidden="true" />
      <span class="cook-timer-time">{{ timerLabel }}</span>
      <span v-if="timerStep !== null" class="cook-timer-step">
        {{ t('recipes.cookMode.timerFor', { n: timerStep + 1 }) }}
      </span>
      <Button
        v-if="timer.running.value"
        icon="mdi mdi-pause"
        text
        rounded
        :aria-label="t('recipes.cookMode.pause')"
        @click="timer.pause()"
      />
      <Button
        v-else
        icon="mdi mdi-play"
        text
        rounded
        :aria-label="t('recipes.cookMode.resume')"
        @click="timer.start()"
      />
      <Button
        icon="mdi mdi-close"
        text
        rounded
        :aria-label="t('recipes.cookMode.resetTimer')"
        @click="timer.reset(); timerStep = null"
      />
    </div>

    <nav class="cook-nav" :aria-label="t('recipes.cookMode.navigation')">
      <Button
        icon="mdi mdi-chevron-left"
        :label="t('recipes.cookMode.prev')"
        severity="secondary"
        outlined
        size="large"
        :disabled="isFirst || showAll || showIntro || askVersion"
        @click="prev"
      />
      <Button
        v-if="!isFinish"
        icon="mdi mdi-chevron-right"
        icon-pos="right"
        :label="index + 1 === stepCount ? t('recipes.cookMode.finish') : t('recipes.cookMode.next')"
        size="large"
        :disabled="!recipe || showAll || showIntro || askVersion"
        @click="next"
      />
      <Button
        v-else
        icon="mdi mdi-restart"
        :label="t('recipes.cookMode.restart')"
        severity="secondary"
        size="large"
        @click="goTo(0)"
      />
    </nav>

    <CookedDialog
      v-if="recipe"
      v-model:visible="cookedOpen"
      :recipe-id="recipe.id"
      :servings="servings"
      :variation-id="variationId"
      @logged="logged = true"
    />
  </div>
</template>

<style scoped lang="scss">
.cook-mode {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  padding: env(safe-area-inset-top, 0px) env(safe-area-inset-right, 0px)
    env(safe-area-inset-bottom, 0px) env(safe-area-inset-left, 0px);
  background: var(--p-content-background);
}

.cook-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
}

.cook-header-title {
  flex: 1;
  min-width: 0;
  text-align: center;
}

.cook-recipe-title {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
}

.cook-progress-label {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.cook-progress {
  height: 0.3rem;
  border-radius: 0;
}

.cook-stage {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  touch-action: pan-y;
}

.cook-screen {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 48rem;
  margin: 0 auto;
  padding: var(--space-5) var(--space-4);
}

.cook-heading {
  font-size: clamp(2rem, 7vw, 3rem);
}

.cook-step-number {
  display: grid;
  place-items: center;
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 50%;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  font-weight: 800;
  font-size: var(--font-size-2xl);
}

// The step text is what the cook reads from a step away, so it scales with
// the screen instead of sitting at body size.
.cook-step-text {
  font-size: clamp(1.4rem, 5.5vw, 2.25rem);
  line-height: 1.45;
}

.cook-image {
  width: 100%;
  max-height: 40vh;
  object-fit: cover;
  border-radius: var(--p-border-radius-lg);
}

.cook-ingredients {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-surface-50);

  h2 {
    font-family: var(--font-head);
    font-weight: 700;
    font-size: var(--font-size-md);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--p-text-muted-color);
  }
}

.p-dark .cook-ingredients {
  background: var(--p-surface-900);
}

.cook-versions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.cook-version {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
  width: 100%;
  min-height: 3.5rem;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  text-align: left;
  cursor: pointer;

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  }
}

.cook-version-name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-xl);
  font-weight: 800;
}

.cook-version-meta {
  color: var(--p-text-muted-color);
}

.cook-first {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.cook-first-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-surface-50);
}

.p-dark .cook-first-item {
  background: var(--p-surface-900);
}

.cook-first-title {
  font-size: clamp(1.15rem, 4.5vw, 1.5rem);
  font-weight: 700;
}

.cook-finish {
  align-items: center;
  text-align: center;
}

.cook-finish-icon {
  font-size: clamp(4rem, 20vw, 7rem);
  color: var(--p-primary-color);
}

.cook-finish-text {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-lg);
}

.cook-logged {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 700;
  color: var(--p-green-600);
}

.cook-timer {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 var(--space-3) var(--space-2);
  padding: var(--space-1) var(--space-2) var(--space-1) var(--space-4);
  border-radius: 2rem;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
}

.cook-timer-time {
  font-size: var(--font-size-2xl);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.cook-timer-step {
  flex: 1;
  font-size: var(--font-size-sm);
}

.cook-nav {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
  padding: var(--space-3);
  border-top: 1px solid var(--p-content-border-color);
}

@media (min-width: $bp-sm) {
  .cook-screen {
    padding: var(--space-6);
  }

  .cook-nav {
    grid-template-columns: minmax(0, 14rem) minmax(0, 14rem);
    justify-content: center;
  }
}
</style>
