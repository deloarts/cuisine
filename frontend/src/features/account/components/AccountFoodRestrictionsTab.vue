<script setup lang="ts">
/**
 * The user's allergies, intolerances and diets. They are private: only this
 * tab reads or writes them, nobody else (admins included) can see them, and
 * they surface as warnings on recipes and shopping items shown to this user.
 * Storing them needs the voluntary health-data consent, asked before the
 * first restriction; withdrawing it deletes every restriction. The opt-in
 * below it lets others plan for this user as a dinner guest; they then only
 * learn that a recipe does not suit their guests, never who or why.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import { ALLERGENS } from '@/shared/cookbook/allergens'
import IngredientOption from '@/shared/cookbook/IngredientOption.vue'
import { DIETS, type Diet } from '@/shared/cookbook/diets'
import type { Allergen, IngredientResponse, RestrictionKind } from '@/shared/cookbook/types'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'
import {
  addFoodRestriction,
  grantConsent,
  listConsents,
  listFoodRestrictions,
  removeFoodRestriction,
  searchIngredients as searchCatalogue,
  updateProfile,
  withdrawConsent,
  type Consent,
  type FoodRestriction,
} from '@/features/account/api/account'
import { consentOf, restrictionNeedsConsent, withdrawWarning } from '@/features/account/consents'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDateTime } from '@/core/utils/dates'

type Restriction = FoodRestriction

const { t, locale } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()
const currentUser = useCurrentUserStore()
const resources = useCookbookResources()

const restrictions = ref<Restriction[]>([])
const kind = ref<RestrictionKind>('allergy')
const target = ref<'allergen' | 'ingredient' | 'family'>('allergen')
// A family covers every variant of a food, also ones added later.
const familyId = ref<string | null>(null)
const allergen = ref<Allergen | null>(null)
const diet = ref<Diet | null>(null)
// A catalogue ingredient, or a name typed in; an unknown name becomes a
// draft ingredient on the server.
const ingredient = ref<IngredientResponse | string | null>(null)
const suggestions = ref<IngredientResponse[]>([])
const note = ref('')
const saving = ref(false)
const sharing = ref(false)
const consents = ref<Consent[]>([])
const consenting = ref(false)

const consent = computed(() => consentOf(consents.value, 'health_data'))
const grantedAt = computed(() =>
  consent.value.granted_at ? formatDateTime(consent.value.granted_at, locale.value as AppLocale) : '',
)

const shareWithHosts = computed(() => currentUser.user?.share_restrictions_with_hosts ?? false)

const kindOptions = computed(() =>
  (['allergy', 'intolerance', 'diet'] as RestrictionKind[]).map((k) => ({
    value: k,
    label: t(`foodRestrictions.kinds.${k}`),
  })),
)
const targetOptions = computed(() => [
  { value: 'allergen', label: t('foodRestrictions.allergen') },
  { value: 'ingredient', label: t('foodRestrictions.ingredient') },
  { value: 'family', label: t('foodRestrictions.family') },
])
const allergenOptions = computed(() => ALLERGENS.map((a) => ({ value: a, label: t(`allergens.${a}`) })))
const dietOptions = computed(() => DIETS.map((d) => ({ value: d, label: t(`diets.${d}`) })))

const ingredientName = computed(() =>
  typeof ingredient.value === 'string' ? ingredient.value.trim() : (ingredient.value?.name ?? ''),
)
const canAdd = computed(() => {
  if (kind.value === 'diet') return diet.value !== null
  if (target.value === 'family') return familyId.value !== null
  return target.value === 'allergen' ? allergen.value !== null : ingredientName.value !== ''
})

function label(r: Restriction): string {
  if (r.diet) return t(`diets.${r.diet}`)
  if (r.allergen) return t(`allergens.${r.allergen}`)
  if (r.family_id) return t('foodRestrictions.familyLabel', { name: r.family_name ?? '?' })
  return r.ingredient_name ?? '?'
}

function severity(r: Restriction): 'danger' | 'warn' | 'info' {
  if (r.kind === 'allergy') return 'danger'
  return r.kind === 'intolerance' ? 'warn' : 'info'
}

async function load() {
  restrictions.value = await listFoodRestrictions()
}

async function searchIngredients(event: { query: string }) {
  try {
    suggestions.value = await searchCatalogue(event.query)
  } catch {
    suggestions.value = []
  }
}

function targetBody() {
  if (kind.value === 'diet') return { diet: diet.value }
  if (target.value === 'allergen') return { allergen: allergen.value }
  if (target.value === 'family') return { family_id: familyId.value }
  const value = ingredient.value
  return value && typeof value === 'object' ? { ingredient_id: value.id } : { ingredient_name: ingredientName.value }
}

function add() {
  if (!canAdd.value) return
  if (!restrictionNeedsConsent(consent.value)) {
    void store()
    return
  }
  confirm.require({
    header: t('consents.health.askTitle'),
    message: t('consents.health.askMessage'),
    acceptProps: { label: t('consents.health.agreeAndAdd') },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void grantThenStore(),
  })
}

async function grantThenStore() {
  consenting.value = true
  try {
    consents.value = await grantConsent('health_data')
  } catch (err) {
    toast.error(err)
    return
  } finally {
    consenting.value = false
  }
  await store()
}

async function store() {
  saving.value = true
  try {
    await addFoodRestriction({ kind: kind.value, note: note.value.trim(), ...targetBody() })
    allergen.value = null
    diet.value = null
    ingredient.value = null
    familyId.value = null
    note.value = ''
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

async function remove(r: Restriction) {
  try {
    await removeFoodRestriction(r.id)
    await load()
  } catch (err) {
    toast.error(err)
  }
}

function setConsent(value: boolean) {
  if (value) {
    void changeConsent(() => grantConsent('health_data'))
    return
  }
  const warning = withdrawWarning('health_data', restrictions.value.length)
  confirm.require({
    header: t('consents.health.withdrawTitle'),
    message: t(warning.key, { count: warning.count }, warning.count),
    acceptProps: { label: t('consents.withdraw'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void changeConsent(() => withdrawConsent('health_data')),
  })
}

async function changeConsent(action: () => Promise<Consent[]>) {
  consenting.value = true
  try {
    consents.value = await action()
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    consenting.value = false
  }
}

async function setSharing(value: boolean) {
  sharing.value = true
  try {
    currentUser.apply(await updateProfile({ share_restrictions_with_hosts: value }))
  } catch (err) {
    toast.error(err)
  } finally {
    sharing.value = false
  }
}

onMounted(() => {
  load().catch((err: unknown) => toast.error(err))
  listConsents()
    .then((list) => (consents.value = list))
    .catch((err: unknown) => toast.error(err))
  resources.load().catch(() => undefined)
})
</script>

<template>
  <div class="settings-tab">
    <Message severity="info" :closable="false">
      <i class="mdi mdi-lock-outline" aria-hidden="true" /> {{ t('foodRestrictions.privacy') }}
    </Message>

    <section class="consent" aria-labelledby="health-consent-title">
      <h2 id="health-consent-title" class="panel-title">{{ t('consents.health.title') }}</h2>
      <p class="hint">{{ t('consents.health.explanation') }}</p>
      <div class="share-row">
        <ToggleSwitch
          :model-value="consent.granted"
          input-id="consent-health"
          :disabled="consenting"
          @update:model-value="setConsent"
        />
        <label for="consent-health">{{ t('consents.health.label') }}</label>
      </div>
      <small class="field-hint">
        {{ consent.granted ? t('consents.grantedAt', { date: grantedAt }) : t('consents.health.missing') }}
      </small>
    </section>

    <div class="share">
      <div class="share-row">
        <ToggleSwitch
          :model-value="shareWithHosts"
          input-id="fr-share"
          :disabled="sharing"
          @update:model-value="setSharing"
        />
        <label for="fr-share">{{ t('foodRestrictions.share') }}</label>
      </div>
      <small class="field-hint">{{ t('foodRestrictions.shareHint') }}</small>
    </div>

    <ul v-if="restrictions.length" class="restrictions">
      <li v-for="r in restrictions" :key="r.id" class="restriction">
        <Tag :value="t(`foodRestrictions.kinds.${r.kind}`)" :severity="severity(r)" />
        <span class="restriction-text">
          <strong>{{ label(r) }}</strong>
          <small v-if="r.note" class="text-muted">{{ r.note }}</small>
        </span>
        <Button
          icon="mdi mdi-delete-outline"
          text
          rounded
          severity="danger"
          :aria-label="t('foodRestrictions.remove', { name: label(r) })"
          @click="remove(r)"
        />
      </li>
    </ul>
    <p v-else class="empty-note">{{ t('foodRestrictions.none') }}</p>

    <form class="add-form" @submit.prevent="add">
      <h3 class="panel-title">{{ t('foodRestrictions.add') }}</h3>
      <SelectButton
        v-model="kind"
        :options="kindOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        :aria-label="t('foodRestrictions.kind')"
      />
      <div v-if="kind === 'diet'" class="field">
        <label id="fr-diet-label" for="fr-diet">{{ t('foodRestrictions.diet') }}</label>
        <Select
          id="fr-diet"
          v-model="diet"
          :options="dietOptions"
          option-label="label"
          option-value="value"
          aria-labelledby="fr-diet-label"
          fluid
        />
      </div>
      <template v-else>
        <SelectButton
          v-model="target"
          :options="targetOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          :aria-label="t('foodRestrictions.target')"
        />
        <div v-if="target === 'allergen'" class="field">
          <label id="fr-allergen-label" for="fr-allergen">{{ t('foodRestrictions.allergen') }}</label>
          <Select
            id="fr-allergen"
            v-model="allergen"
            :options="allergenOptions"
            option-label="label"
            option-value="value"
            aria-labelledby="fr-allergen-label"
            fluid
          />
        </div>
        <div v-else-if="target === 'family'" class="field">
          <label id="fr-family-label" for="fr-family">{{ t('foodRestrictions.family') }}</label>
          <Select
            id="fr-family"
            v-model="familyId"
            :options="resources.families.value"
            option-label="name"
            option-value="id"
            aria-labelledby="fr-family-label"
            filter
            fluid
          />
          <small class="field-hint">{{ t('foodRestrictions.familyHint') }}</small>
        </div>
        <div v-else class="field">
          <label for="fr-ingredient">{{ t('foodRestrictions.ingredient') }}</label>
          <AutoComplete
            v-model="ingredient"
            input-id="fr-ingredient"
            :suggestions="suggestions"
            option-label="name"
            :placeholder="t('foodRestrictions.ingredientSearch')"
            fluid
            @complete="searchIngredients"
          >
            <template #option="{ option }">
              <IngredientOption :ingredient="option" :meta="['family', 'allergens', 'draft']" />
            </template>
          </AutoComplete>
          <small class="field-hint">{{ t('foodRestrictions.ingredientHint') }}</small>
        </div>
      </template>
      <div class="field">
        <label for="fr-note">{{ t('foodRestrictions.note') }}</label>
        <InputText id="fr-note" v-model="note" :placeholder="t('foodRestrictions.notePlaceholder')" fluid />
      </div>
      <div>
        <Button type="submit" :label="t('foodRestrictions.add')" icon="mdi mdi-plus" :loading="saving || consenting" :disabled="!canAdd" />
      </div>
    </form>
  </div>
</template>

<style scoped lang="scss">
.consent,
.share {
  display: grid;
  gap: var(--space-1);
}

.share-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.restrictions {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  margin: 0;
  list-style: none;
}

.restriction {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
}

.restriction-text {
  display: grid;
}

.add-form {
  display: grid;
  gap: var(--space-3);
  max-width: 32rem;
}
</style>
