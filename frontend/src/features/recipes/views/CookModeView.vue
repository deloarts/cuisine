<script setup lang="ts">
/**
 * Cook mode: the recipe full screen, in big type, with each step's
 * ingredients scaled to the servings chosen on the recipe page. It has two
 * layouts the cook switches between at any time, and the choice is saved on
 * the account: step mode shows one step per screen, moved through with
 * swipes, the arrow keys or the buttons; flow mode shows every step in one
 * scrolling column and highlights the one being read. A step with a duration
 * offers a timer, and the screen stays on while cooking unless the reader
 * turned that off on the account page. Before step 1 come the sub-recipes to
 * make first and the equipment to set out, marking what the kitchen lacks.
 * "Finish" on the last step logs the meal in the cooking calendar, at most
 * once a day and without a word, and leaves cook mode; a sub-recipe opened
 * from its parent is not logged and leads back to the parent. A recipe with
 * variations first asks which version to cook, unless the link says, and
 * cooks the chosen variation as the backend applies it.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { onKeyStroke, useSwipe } from '@vueuse/core'

import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import {
  getRecipe,
  listVariations,
  logCookOnce,
  saveCookModeLayout,
  viewVariation,
  type CookModeLayout,
  type RecipeDetailResponse,
  type StepMarkerView,
  type VariationResponse,
} from '@/features/recipes/api/recipes'
import CookIntro from '@/features/recipes/components/CookIntro.vue'
import CookStep from '@/features/recipes/components/CookStep.vue'
import IngredientLines from '@/features/recipes/components/IngredientLines.vue'
import ServingsStepper from '@/features/recipes/components/ServingsStepper.vue'
import { useCookMode, useStepTimer } from '@/features/recipes/composables/useCookMode'
import { useCookSteps } from '@/features/recipes/composables/useCookSteps'
import { isoDay } from '@/features/recipes/utils/dates'
import { setOutList } from '@/features/recipes/utils/equipment'
import { scaleFactor } from '@/features/recipes/utils/scaling'
import { ORIGINAL, authorName, cookVersion } from '@/features/recipes/utils/variations'
import EmptyState from '@/shared/components/EmptyState.vue'
import { useKeepScreenOn } from '@/shared/composables/useKeepScreenOn'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()
const currentUser = useCurrentUserStore()

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
const factor = computed(() =>
  recipe.value ? scaleFactor(servings.value, recipe.value.base_servings) : 1,
)
const firstNeeds = computed(() =>
  (recipe.value?.needs ?? []).map((need) => ({
    ...need,
    batches: need.batches * factor.value,
  })),
)
const setOut = computed(() => setOutList(recipe.value?.equipment ?? []))
const hasIntro = computed(() => firstNeeds.value.length > 0 || setOut.value.length > 0)
// The kitchen's gaps, from the "You'll need" list, marked on every step.
const missingIds = computed(
  () => new Set(setOut.value.filter((n) => n.missing === true).map((n) => n.equipment.id)),
)
const showAll = ref(false)

const { steps: cookSteps, allIngredients } = useCookSteps({
  recipe,
  markers,
  variationId,
  factor,
  missingIds,
})
const stepCount = computed(() => cookSteps.value.length)
const { index, isFirst, isLast, progress, next, prev, goTo } = useCookMode(stepCount)
const current = computed(() => cookSteps.value[index.value] ?? null)

// The layout comes from the account; switching saves it there right away
// and goes back when the save fails, so the switch never lies.
const layout = ref<CookModeLayout>(currentUser.user?.cook_mode_layout ?? 'step')
const flow = computed(() => layout.value === 'flow')

async function toggleLayout() {
  const before = layout.value
  layout.value = before === 'flow' ? 'step' : 'flow'
  try {
    currentUser.apply(await saveCookModeLayout(layout.value))
  } catch (err) {
    layout.value = before
    toast.error(err)
  }
}

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

function startTimer(step: number) {
  const minutes = cookSteps.value[step]?.step.duration_minutes
  if (!minutes) return
  timerStep.value = step
  timer.start(minutes)
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
  let shown = original
  markers.value = []
  if (chosen) {
    const view = await viewVariation(original.id, chosen)
    shown = view.recipe
    markers.value = view.steps
  }
  variationId.value = chosen
  recipe.value = shown
  // Opened as a sub-recipe: as many servings as the batches the parent needs.
  const batches = Number(route.query.batches)
  if (batches > 0) servings.value = Math.max(1, Math.round(batches * shown.base_servings))
  if (!servings.value) servings.value = shown.base_servings
  showIntro.value = shown.needs.length > 0 || shown.equipment.length > 0
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

function close() {
  if (window.history.state?.back) router.back()
  else void router.push({ name: 'recipe', params: { id: String(route.params.id) } })
}

// Finishing logs the meal once a day, silently: a failed log never keeps
// the cook in cook mode. Drafts stay out of the history, and a sub-recipe is
// part of its parent's meal.
const finishing = ref(false)
async function finish() {
  if (finishing.value || !recipe.value) return
  finishing.value = true
  if (recipe.value.status === 'published' && !parentId.value) {
    try {
      await logCookOnce(recipe.value.id, isoDay(), servings.value, variationId.value)
    } catch {
      // Logging is a convenience here; "I cooked this" on the recipe page remains.
    }
  }
  finishing.value = false
  if (parentId.value) backToParent()
  else close()
}

// Moving between a recipe and its sub-recipe reuses this view, so a new id
// starts over.
watch(
  () => route.params.id,
  (nextId, previousId) => {
    if (nextId === previousId) return
    recipe.value = null
    failed.value = false
    variations.value = []
    variationId.value = null
    askVersion.value = false
    markers.value = []
    servings.value = Number(route.query.servings) || 0
    goTo(0)
    void load()
  },
)

const stage = useTemplateRef<HTMLElement>('stage')
const { direction } = useSwipe(stage, {
  threshold: 60,
  onSwipeEnd: () => {
    // Flow mode scrolls instead.
    if (flow.value) return
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

// ── Flow mode ────────────────────────────────────────────────────────
// The current step is the one crossing a line near the top of the column,
// and the last one once the column is scrolled to its end. Moving by key or
// by a tap on a step's number scrolls that step to the top.

function stepElement(step: number): HTMLElement | null {
  return stage.value?.querySelector<HTMLElement>(`[data-step-index="${step}"]`) ?? null
}

function scrollToStep(step: number, behavior: ScrollBehavior = 'smooth') {
  stepElement(step)?.scrollIntoView({ block: 'start', behavior })
}

function selectStep(step: number) {
  goTo(step)
  scrollToStep(index.value)
}

let observer: IntersectionObserver | null = null

function observeSteps() {
  observer?.disconnect()
  observer = null
  const root = stage.value
  if (!flow.value || !root || typeof IntersectionObserver === 'undefined') return
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) index.value = Number((entry.target as HTMLElement).dataset.stepIndex)
      }
    },
    { root, rootMargin: '-12% 0px -87% 0px' },
  )
  root.querySelectorAll('[data-step-index]').forEach((el) => observer?.observe(el))
}

function onStageScroll() {
  const root = stage.value
  if (!flow.value || !root) return
  if (root.scrollTop > 0 && root.scrollTop + root.clientHeight >= root.scrollHeight - 2) {
    goTo(stepCount.value - 1)
  }
}

// Switching keeps the place: flow mode opens at the step step mode showed,
// and step mode at the step flow mode highlighted.
watch(flow, async (on) => {
  await nextTick()
  if (on) scrollToStep(index.value, 'auto')
  observeSteps()
})
watch([stepCount, askVersion], async () => {
  await nextTick()
  observeSteps()
})
// Back from all ingredients, flow mode returns to the step it was on.
watch(showAll, async (open) => {
  await nextTick()
  observeSteps()
  if (flow.value && !open) scrollToStep(index.value, 'auto')
})

onKeyStroke(['ArrowRight', 'PageDown'], (e) => {
  if (flow.value) {
    if (e.key !== 'ArrowRight' || askVersion.value || showAll.value) return
    e.preventDefault()
    selectStep(index.value + 1)
    return
  }
  e.preventDefault()
  forward()
})
onKeyStroke(['ArrowLeft', 'PageUp'], (e) => {
  if (flow.value) {
    if (e.key !== 'ArrowLeft' || askVersion.value || showAll.value) return
    e.preventDefault()
    selectStep(index.value - 1)
    return
  }
  e.preventDefault()
  prev()
})

onMounted(() => {
  void load()
})

onBeforeUnmount(() => {
  timer.stop()
  observer?.disconnect()
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
        <p v-if="recipe && stepCount && !askVersion" class="cook-progress-label" data-testid="cook-step-label">
          {{ t('recipes.cookMode.step', { n: index + 1, total: stepCount }) }}
        </p>
      </div>
      <Button
        :icon="flow ? 'mdi mdi-view-carousel-outline' : 'mdi mdi-view-agenda-outline'"
        text
        rounded
        severity="secondary"
        data-testid="cook-layout-toggle"
        :aria-label="flow ? t('recipes.cookMode.showSteps') : t('recipes.cookMode.showFlow')"
        :aria-pressed="flow"
        @click="toggleLayout"
      />
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

    <div v-if="recipe" ref="stage" class="cook-stage" aria-live="polite" @scroll.passive="onStageScroll">
      <section v-if="askVersion" class="cook-screen" data-testid="cook-choose">
        <h1 class="cook-heading">{{ t('recipes.cookMode.chooseTitle') }}</h1>
        <p class="cook-muted">{{ t('recipes.cookMode.chooseText') }}</p>
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

      <div v-else-if="flow" class="cook-screen cook-flow" data-testid="cook-flow">
        <CookIntro v-if="hasIntro" :needs="firstNeeds" :set-out="setOut" @cook-first="cookFirst" />
        <ol class="cook-flow-steps">
          <li v-for="(view, i) in cookSteps" :key="view.step.position" :data-step-index="i">
            <CookStep
              :view="view"
              :number="i + 1"
              :timing="timerStep === i"
              :current="index === i"
              selectable
              @start-timer="startTimer(i)"
              @select="selectStep(i)"
            />
          </li>
        </ol>
        <Button
          :label="t('recipes.cookMode.finish')"
          icon="mdi mdi-check"
          size="large"
          class="cook-flow-finish"
          data-testid="cook-finish"
          :loading="finishing"
          @click="finish"
        />
      </div>

      <section v-else-if="showIntro" class="cook-screen">
        <CookIntro :needs="firstNeeds" :set-out="setOut" @cook-first="cookFirst" />
        <Button
          :label="t('recipes.cookMode.startSteps')"
          icon="mdi mdi-chevron-right"
          icon-pos="right"
          size="large"
          @click="showIntro = false"
        />
      </section>

      <section v-else-if="current" :key="index" class="cook-screen" data-testid="cook-step">
        <CookStep :view="current" :number="index + 1" :timing="timerStep === index" @start-timer="startTimer(index)" />
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

    <nav v-if="!flow" class="cook-nav" :aria-label="t('recipes.cookMode.navigation')">
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
        v-if="!isLast"
        icon="mdi mdi-chevron-right"
        icon-pos="right"
        :label="t('recipes.cookMode.next')"
        size="large"
        data-testid="cook-next"
        :disabled="!recipe || showAll || showIntro || askVersion"
        @click="next"
      />
      <Button
        v-else
        icon="mdi mdi-check"
        :label="t('recipes.cookMode.finish')"
        size="large"
        data-testid="cook-finish"
        :loading="finishing"
        :disabled="!recipe || showAll || showIntro || askVersion"
        @click="finish"
      />
    </nav>
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

.cook-muted {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-lg);
}

.cook-flow-steps {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;

  > li {
    scroll-margin-top: var(--space-3);
  }
}

// Flow mode's steps sit on cards; the current one carries the primary colour
// on its border, so the eye finds it again after looking at the pan.
.cook-flow-steps :deep(.cook-step) {
  padding: var(--space-4);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  transition: border-color 0.2s;
}

.cook-flow-steps :deep(.cook-step--current) {
  border-color: var(--p-primary-color);
}

.cook-flow-finish {
  align-self: center;
  min-width: min(100%, 14rem);
  margin-bottom: var(--space-6);
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
