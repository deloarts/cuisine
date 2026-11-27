<script setup lang="ts">
/**
 * Creates or edits one catalogue ingredient: its names and aliases per
 * language, its family, the category that sorts it on the shopping list,
 * nutrition per 100 g with the optional extended nutrients (typed in or
 * taken over from USDA FoodData Central), the density and per-unit weights
 * that turn "2 pieces" or "1 tbsp" into grams, its allergens, diet markers
 * and season months. Someone who may not edit it sees the same form
 * read-only. Creating warns about near duplicates ("Did you mean
 * Erdapfel?"); deleting and merging go through the deletion dialog.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { watchDebounced } from '@vueuse/core'

import PageHeader from '@/shared/components/PageHeader.vue'
import FieldSkeleton from '@/shared/components/skeleton/FieldSkeleton.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import { ALLERGENS } from '@/shared/cookbook/allergens'
import { CONTENT_LOCALES, contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { DIET_MARKERS, type DietMarker } from '@/shared/cookbook/diets'
import TranslationFields from '@/shared/cookbook/TranslationFields.vue'
import UnitSelect from '@/shared/cookbook/UnitSelect.vue'
import type { Allergen, ContentLocale } from '@/shared/cookbook/types'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'
import {
  activateIngredient,
  createIngredient,
  extendedNutrients,
  getIngredient,
  ingredientDeletionImpact,
  ingredientDuplicates,
  nutritionSources,
  updateIngredient,
  type DuplicateCandidate,
  type ExtendedNutrient,
  type IngredientDetail,
} from '@/features/ingredients/api/ingredients'
import IngredientDeleteDialog from '@/features/ingredients/components/IngredientDeleteDialog.vue'
import SeasonPicker from '@/features/ingredients/components/SeasonPicker.vue'
import UsdaLookupDialog from '@/features/ingredients/components/UsdaLookupDialog.vue'
import { emptyNutrition, mergeNutrition, NUTRITION_FIELDS, type Nutrition } from '@/features/ingredients/nutrition'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import ContentCard from '@/shared/components/ContentCard.vue'

type FoodMatch = Schemas['FoodMatchResponse']

interface ConversionRow {
  unit_id: string | null
  grams: number | null
}

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const resources = useCookbookResources()

const id = computed(() => (typeof route.params.id === 'string' ? route.params.id : null))
const detail = ref<IngredientDetail | null>(null)
const loading = ref(false)
const saving = ref(false)
const usdaOpen = ref(false)

const originalLocale = ref<ContentLocale>(contentLocaleOf(locale.value))
const texts = ref<Record<string, Record<string, string>>>({})
const categoryId = ref<string | null>(null)
const nutrition = ref<Nutrition>(emptyNutrition())
const nutritionSource = ref<'manual' | 'usda'>('manual')
const usdaFdcId = ref<number | null>(null)
const density = ref<number | null>(null)
const conversions = ref<ConversionRow[]>([])
const allergens = ref<Allergen[]>([])
const dietMarkers = ref<DietMarker[]>([])
const familyId = ref<string | null>(null)
const aliases = ref<Record<string, string[]>>({})
const extended = ref<Record<string, number | null>>({})
const seasonMonths = ref<number[]>([])

const seeded = ref(false)
const deleteOpen = ref(false)
const deleteMode = ref<'delete' | 'merge'>('delete')
const duplicates = ref<DuplicateCandidate[]>([])
const credit = ref('')
const citation = ref('')
const nutrientCatalogue = ref<ExtendedNutrient[]>([])
const showMoreNutrients = ref(false)

const canEdit = computed(() =>
  detail.value ? detail.value.can_edit : currentUser.hasPermission(Permission.WRITE_INGREDIENTS),
)
const title = computed(() =>
  detail.value ? detail.value.name : t('ingredients.create'),
)
const localeOptions = computed(() =>
  CONTENT_LOCALES.map((l) => ({ value: l, label: t(`contentLocales.${l.replace('-', '')}`) })),
)
const originalName = computed(() => texts.value[originalLocale.value]?.name?.trim() ?? '')
const canMerge = computed(() => currentUser.hasPermission(Permission.MANAGE_INGREDIENTS))
const extendedCount = computed(() => Object.values(extended.value).filter((v) => v !== null && v !== undefined).length)
const exactDuplicate = computed(() => duplicates.value.find((d) => d.exact) ?? null)
const nearDuplicates = computed(() => duplicates.value.filter((d) => !d.exact))

function fill(d: IngredientDetail | null) {
  detail.value = d
  originalLocale.value = (d?.original_locale as ContentLocale | undefined) ?? contentLocaleOf(locale.value)
  texts.value = structuredClone(d?.translations ?? {})
  categoryId.value = d?.category?.id ?? null
  nutrition.value = d ? { ...emptyNutrition(), ...d.nutrition } : emptyNutrition()
  nutritionSource.value = d?.nutrition_source === 'usda' ? 'usda' : 'manual'
  usdaFdcId.value = d?.usda_fdc_id ?? null
  density.value = d?.density_g_per_ml ?? null
  conversions.value = d?.conversions.map((c) => ({ unit_id: c.unit_id, grams: c.grams })) ?? []
  allergens.value = (d?.allergens ?? []) as Allergen[]
  dietMarkers.value = (d?.diet_markers ?? []) as DietMarker[]
  familyId.value = d?.family?.id ?? null
  aliases.value = Object.fromEntries(CONTENT_LOCALES.map((l) => [l, [...(d?.aliases[l] ?? [])]]))
  extended.value = { ...d?.extended_nutrition }
  seasonMonths.value = [...(d?.season_months ?? [])]
  showMoreNutrients.value = Object.keys(extended.value).length > 0
  duplicates.value = []
  seeded.value = false
  if (d?.can_edit) void loadSeeded(d.id)
}

// A seeded ingredient cannot be deleted, so its editor hides the button.
async function loadSeeded(ingredientId: string) {
  try {
    const impact = await ingredientDeletionImpact(ingredientId)
    if (detail.value?.id === ingredientId) seeded.value = impact.seeded
  } catch {
    seeded.value = false
  }
}

async function load() {
  if (!id.value) {
    fill(null)
    return
  }
  loading.value = true
  try {
    fill(await getIngredient(id.value))
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

function applyUsda(match: FoodMatch) {
  nutrition.value = mergeNutrition(nutrition.value, match.nutrition)
  const found = Object.entries(match.extended_nutrition ?? {})
  if (found.length) {
    extended.value = { ...extended.value, ...Object.fromEntries(found.map(([k, v]) => [k, Math.round(v * 1000) / 1000])) }
    showMoreNutrients.value = true
  }
  nutritionSource.value = 'usda'
  usdaFdcId.value = match.fdc_id
}

function markManual() {
  nutritionSource.value = 'manual'
  usdaFdcId.value = null
}

function addConversion() {
  conversions.value.push({ unit_id: null, grams: null })
}

function body() {
  return {
    original_locale: originalLocale.value,
    translations: Object.fromEntries(
      Object.entries(texts.value)
        .filter(([, v]) => (v.name ?? '').trim())
        .map(([l, v]) => {
          const name = (v.name ?? '').trim()
          return [l, { name, plural_name: (v.plural_name ?? '').trim() || name }]
        }),
    ),
    category_id: categoryId.value,
    family_id: familyId.value,
    aliases: Object.fromEntries(
      Object.entries(aliases.value).map(([l, names]) => [l, [...new Set(names.map((n) => n.trim()).filter(Boolean))]]),
    ),
    nutrition: nutrition.value,
    extended_nutrition: Object.fromEntries(
      Object.entries(extended.value).filter((entry): entry is [string, number] => entry[1] !== null && entry[1] !== undefined),
    ),
    season_months: seasonMonths.value,
    density_g_per_ml: density.value,
    conversions: conversions.value
      .filter((c): c is { unit_id: string; grams: number } => c.unit_id !== null && c.grams !== null && c.grams > 0)
      .map((c) => ({ unit_id: c.unit_id, grams: c.grams })),
    allergens: allergens.value,
    diet_markers: dietMarkers.value,
    nutrition_source: nutritionSource.value,
    usda_fdc_id: nutritionSource.value === 'usda' ? usdaFdcId.value : null,
  }
}

async function save() {
  if (!originalName.value) {
    toast.error(null, 'ingredients.nameRequired')
    return
  }
  saving.value = true
  try {
    if (id.value) {
      await updateIngredient(id.value, body())
      await load()
    } else {
      const created = await createIngredient(body())
      await router.replace({ name: 'ingredient', params: { id: created.id } })
    }
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

async function activate() {
  if (!id.value) return
  try {
    await activateIngredient(id.value)
    toast.success(t('ingredients.activated'))
    await load()
  } catch (err) {
    toast.error(err)
  }
}

function openDelete(mode: 'delete' | 'merge') {
  deleteMode.value = mode
  deleteOpen.value = true
}

function onMerged(target: IngredientDetail) {
  void router.push({ name: 'ingredient', params: { id: target.id } })
}

// While creating, the original name is checked for ingredients that probably
// mean the same food, so nobody adds "Erdäpfel" next to "Erdapfel".
watchDebounced(
  [originalName, originalLocale],
  async ([name, nameLocale]) => {
    if (id.value || name.length < 2) {
      duplicates.value = []
      return
    }
    try {
      const found = await ingredientDuplicates(name, nameLocale)
      if (originalName.value === name) duplicates.value = found
    } catch {
      duplicates.value = []
    }
  },
  { debounce: 400 },
)

watch(id, () => void load())
onMounted(() => {
  void load()
  resources.load().catch((err: unknown) => toast.error(err))
  nutritionSources()
    .then((sources) => {
      credit.value = sources.credit[contentLocaleOf(locale.value)] ?? sources.credit['en-GB'] ?? ''
      citation.value = sources.citation
    })
    .catch(() => undefined)
  extendedNutrients()
    .then((catalogue) => {
      nutrientCatalogue.value = catalogue
    })
    .catch(() => undefined)
})
</script>

<template>
  <section class="ingredient-edit">
    <PageHeader :title="title">
      <Button
        :label="t('common.back')"
        icon="mdi mdi-arrow-left"
        text
        @click="router.push({ name: 'ingredients' })"
      />
    </PageHeader>

    <Message v-if="detail?.status === 'draft'" severity="warn" class="draft-note">
      <div class="draft-row">
        <span>{{ t('ingredients.draftNote') }}</span>
        <Button v-if="detail.can_edit" :label="t('ingredients.activate')" icon="mdi mdi-check" size="small" @click="activate" />
      </div>
    </Message>
    <p v-if="detail && !detail.can_edit" class="hint read-only-hint">{{ t('ingredients.readOnly') }}</p>

    <SkeletonRegion v-if="loading" class="edit-form" testid="ingredient-skeleton">
      <ContentCard class="section">
        <Skeleton width="25%" height="1.25rem" />
        <div class="form-grid">
          <FieldSkeleton v-for="n in 3" :key="n" />
        </div>
        <div class="form-grid">
          <FieldSkeleton v-for="n in 2" :key="n" label-width="20%" />
        </div>
        <div class="alias-grid">
          <FieldSkeleton v-for="n in 2" :key="n" label-width="45%" />
        </div>
      </ContentCard>
      <ContentCard class="section">
        <Skeleton width="30%" height="1.25rem" />
        <div class="form-grid">
          <FieldSkeleton v-for="n in 6" :key="n" label-width="50%" />
        </div>
      </ContentCard>
      <ContentCard class="section">
        <Skeleton width="35%" height="1.25rem" />
        <FieldSkeleton label-width="25%" />
      </ContentCard>
    </SkeletonRegion>

    <form v-else class="edit-form" @submit.prevent="save">
      <ContentCard class="section">
        <h3 class="panel-title">{{ t('ingredients.sections.names') }}</h3>
        <div class="form-grid">
          <div class="field">
            <label id="ing-locale-label" for="ing-locale">{{ t('ingredients.originalLocale') }}</label>
            <Select
              id="ing-locale"
              v-model="originalLocale"
              :options="localeOptions"
              option-label="label"
              option-value="value"
              aria-labelledby="ing-locale-label"
              :disabled="!canEdit"
              fluid
            />
          </div>
          <div class="field">
            <label id="ing-category-label" for="ing-category">{{ t('ingredients.category') }}</label>
            <Select
              id="ing-category"
              v-model="categoryId"
              :options="resources.categories.value"
              option-label="name"
              option-value="id"
              aria-labelledby="ing-category-label"
              :placeholder="t('ingredients.noCategory')"
              :disabled="!canEdit"
              show-clear
              fluid
            />
          </div>
          <div class="field">
            <label id="ing-family-label" for="ing-family">{{ t('ingredients.family') }}</label>
            <Select
              id="ing-family"
              v-model="familyId"
              :options="resources.families.value"
              option-label="name"
              option-value="id"
              aria-labelledby="ing-family-label"
              :placeholder="t('ingredients.noFamily')"
              :disabled="!canEdit"
              show-clear
              filter
              fluid
            />
            <small class="field-hint">{{ t('ingredients.familyHint') }}</small>
          </div>
        </div>
        <TranslationFields
          v-model="texts"
          id-prefix="ing"
          :original-locale="originalLocale"
          :disabled="!canEdit"
          :fields="[
            { key: 'name', label: t('common.name') },
            { key: 'plural_name', label: t('ingredients.plural') },
          ]"
        >
          <template #locale="{ locale: l }">
            <div class="field">
              <label :for="`ing-alias-${l}`">{{ t('ingredients.otherNames') }}</label>
              <AutoComplete
                v-model="aliases[l]"
                :input-id="`ing-alias-${l}`"
                multiple
                :typeahead="false"
                :disabled="!canEdit"
                :class="{ 'aliases-read-only': !canEdit }"
                fluid
              />
            </div>
          </template>
        </TranslationFields>
        <Message v-if="exactDuplicate" severity="error" :closable="false">
          {{ t('ingredients.duplicates.exact', { name: exactDuplicate.name }) }}
          <RouterLink :to="{ name: 'ingredient', params: { id: exactDuplicate.id } }">
            {{ t('ingredients.duplicates.open') }}
          </RouterLink>
        </Message>
        <Message v-else-if="nearDuplicates.length" severity="warn" :closable="false">
          <span>{{ t('ingredients.duplicates.didYouMean') }}</span>
          <span v-for="(candidate, index) in nearDuplicates" :key="candidate.id">
            <RouterLink :to="{ name: 'ingredient', params: { id: candidate.id } }">{{ candidate.name }}</RouterLink>
            <small v-if="candidate.matched !== candidate.name" class="text-muted">
              ({{ t('ingredients.duplicates.alias', { name: candidate.matched }) }})</small
            >{{ index < nearDuplicates.length - 1 ? ', ' : '?' }}
          </span>
        </Message>
        <small class="field-hint">{{ t('ingredients.aliasesHint') }}</small>
      </ContentCard>

      <ContentCard class="section">
        <div class="section-head">
          <h3 class="panel-title">{{ t('ingredients.sections.nutrition') }}</h3>
          <Button
            v-if="canEdit"
            type="button"
            :label="t('ingredients.usda.open')"
            icon="mdi mdi-database-search-outline"
            outlined
            size="small"
            @click="usdaOpen = true"
          />
        </div>
        <p class="hint">{{ t('ingredients.per100') }}</p>
        <div class="nutrition-grid">
          <div v-for="field in NUTRITION_FIELDS" :key="field.key" class="field">
            <label :for="`ing-n-${field.key}`">{{ t(`ingredients.nutrition.${field.key}`) }} ({{ field.unit }})</label>
            <InputNumber
              v-model="nutrition[field.key]"
              :input-id="`ing-n-${field.key}`"
              :min="0"
              :max-fraction-digits="2"
              :disabled="!canEdit"
              fluid
            />
          </div>
        </div>
        <div v-if="nutrientCatalogue.length" class="more-nutrients">
          <Button
            type="button"
            :label="t('ingredients.moreNutrients', { count: extendedCount })"
            :icon="showMoreNutrients ? 'mdi mdi-chevron-up' : 'mdi mdi-chevron-down'"
            text
            size="small"
            :aria-expanded="showMoreNutrients"
            aria-controls="ing-more-nutrients"
            @click="showMoreNutrients = !showMoreNutrients"
          />
          <div v-show="showMoreNutrients" id="ing-more-nutrients" class="nutrition-grid">
            <div v-for="nutrient in nutrientCatalogue" :key="nutrient.key" class="field">
              <label :for="`ing-x-${nutrient.key}`">
                {{ t(nutrient.label_key) }} ({{ nutrient.unit === 'ug' ? 'µg' : nutrient.unit }})
              </label>
              <InputNumber
                v-model="extended[nutrient.key]"
                :input-id="`ing-x-${nutrient.key}`"
                :min="0"
                :max-fraction-digits="3"
                :disabled="!canEdit"
                fluid
              />
            </div>
          </div>
        </div>
        <p v-if="nutritionSource === 'usda'" class="field-hint source-line">
          <span :title="citation">{{ credit || t('ingredients.usda.source') }}</span>
          <span>{{ t('ingredients.usda.food', { id: usdaFdcId ?? '?' }) }}</span>
          <Button
            v-if="canEdit"
            type="button"
            :label="t('ingredients.usda.markManual')"
            text
            size="small"
            @click="markManual"
          />
        </p>
      </ContentCard>

      <ContentCard class="section">
        <h3 class="panel-title">{{ t('ingredients.sections.conversions') }}</h3>
        <p class="hint">{{ t('ingredients.conversionsHint') }}</p>
        <div class="field density">
          <label for="ing-density">{{ t('ingredients.density') }}</label>
          <InputNumber
            v-model="density"
            input-id="ing-density"
            :min="0"
            :max-fraction-digits="3"
            suffix=" g/ml"
            :disabled="!canEdit"
            fluid
          />
        </div>
        <ul class="conversion-list">
          <li v-for="(row, index) in conversions" :key="index" class="conversion-row">
            <span class="conversion-one">1</span>
            <UnitSelect
              v-model="row.unit_id"
              :units="resources.units.value"
              :aria-label="t('ingredients.conversionUnit')"
              :disabled="!canEdit"
              class="conversion-unit"
            />
            <span>=</span>
            <InputNumber
              v-model="row.grams"
              :min="0"
              :max-fraction-digits="2"
              suffix=" g"
              :aria-label="t('ingredients.conversionGrams')"
              :disabled="!canEdit"
              class="conversion-grams"
            />
            <Button
              v-if="canEdit"
              type="button"
              icon="mdi mdi-close"
              text
              rounded
              severity="secondary"
              :aria-label="t('common.delete')"
              @click="conversions.splice(index, 1)"
            />
          </li>
        </ul>
        <div v-if="canEdit">
          <Button type="button" :label="t('ingredients.addConversion')" icon="mdi mdi-plus" text @click="addConversion" />
        </div>
      </ContentCard>

      <ContentCard class="section">
        <h3 class="panel-title">{{ t('ingredients.allergens') }}</h3>
        <div class="allergen-grid">
          <div v-for="a in ALLERGENS" :key="a" class="allergen-option">
            <Checkbox v-model="allergens" :input-id="`ing-a-${a}`" :value="a" :disabled="!canEdit" />
            <label :for="`ing-a-${a}`">{{ t(`allergens.${a}`) }}</label>
          </div>
        </div>
      </ContentCard>

      <ContentCard class="section">
        <h3 class="panel-title">{{ t('ingredients.dietMarkers') }}</h3>
        <p class="hint">{{ t('ingredients.dietMarkersHint') }}</p>
        <div class="allergen-grid">
          <div v-for="m in DIET_MARKERS" :key="m" class="allergen-option">
            <Checkbox v-model="dietMarkers" :input-id="`ing-d-${m}`" :value="m" :disabled="!canEdit" />
            <label :for="`ing-d-${m}`">{{ t(`dietMarkers.${m}`) }}</label>
          </div>
        </div>
      </ContentCard>

      <ContentCard class="section">
        <h3 id="ing-season-label" class="panel-title">{{ t('ingredients.season.title') }}</h3>
        <p class="hint">{{ t('ingredients.season.hint') }}</p>
        <SeasonPicker v-model="seasonMonths" labelledby="ing-season-label" :disabled="!canEdit" />
      </ContentCard>

      <p v-if="detail" class="text-muted meta">
        {{ t('ingredients.usedIn', { count: detail.recipe_count }, detail.recipe_count) }}
        <template v-if="detail.owner"> · {{ t('ingredients.createdBy', { name: detail.owner.display_name }) }}</template>
      </p>

      <div v-if="canEdit" class="form-actions">
        <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" />
        <Button
          v-if="detail && canMerge"
          type="button"
          :label="t('ingredients.merge.open')"
          icon="mdi mdi-call-merge"
          text
          @click="openDelete('merge')"
        />
        <Button
          v-if="detail && !seeded"
          type="button"
          :label="t('common.delete')"
          icon="mdi mdi-delete-outline"
          severity="danger"
          text
          @click="openDelete('delete')"
        />
        <small v-if="detail && seeded" class="text-muted seeded-note">{{ t('ingredients.seededNote') }}</small>
      </div>
    </form>

    <IngredientDeleteDialog
      v-if="detail"
      v-model:visible="deleteOpen"
      :ingredient-id="detail.id"
      :name="detail.name"
      :mode="deleteMode"
      @deleted="router.push({ name: 'ingredients' })"
      @merged="onMerged"
    />
    <UsdaLookupDialog v-model:visible="usdaOpen" :initial-query="originalName" @pick="applyUsda" />
  </section>
</template>

<style scoped lang="scss">

.edit-form {
  display: grid;
  gap: var(--space-3);
}

.section {
  display: grid;
  gap: var(--space-3);
}

.section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.draft-note {
  margin-bottom: var(--space-3);
}

.draft-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.nutrition-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  // The fields sit on the row's foot, so a label that wraps onto two lines
  // does not push its input below the one beside it.
  align-items: end;
  gap: var(--space-2) var(--space-3);
}

.source-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.density {
  max-width: 14rem;
}

.conversion-list {
  display: grid;
  gap: var(--space-2);
  padding: 0;
  margin: 0;
  list-style: none;
}

.conversion-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto minmax(0, 7rem) auto;
  align-items: center;
  gap: var(--space-2);
}

.conversion-unit,
.conversion-grams {
  width: 100%;
  min-width: 0;
}

// The number field's own input has a natural width wider than a phone's
// column, so it is told to fit the cell instead.
.conversion-grams :deep(input) {
  width: 100%;
  min-width: 0;
}

.allergen-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}

.allergen-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.alias-grid {
  display: grid;
  gap: var(--space-2) var(--space-3);
}

.more-nutrients {
  display: grid;
  gap: var(--space-2);
}

.seeded-note {
  align-self: center;
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.meta {
  font-size: var(--font-size-sm);
}

@media (min-width: $bp-sm) {
  .nutrition-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .allergen-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .alias-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.read-only-hint {
  margin-bottom: var(--space-3);
}

// A read-only alias list shows its names without the chips' remove icons.
.aliases-read-only :deep([data-pc-section='removeicon']) {
  display: none;
}
</style>
