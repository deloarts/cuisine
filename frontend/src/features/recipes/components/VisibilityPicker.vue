<script setup lang="ts">
/**
 * Who may read a recipe, narrowest first: only its owner, the owner's
 * household, chosen people and groups, everybody signed in, everybody signed
 * in plus every paired instance, or anyone on the internet. Drafts stay with
 * their owner whatever is picked here. The instance may lock the choice, then
 * the picker shows the level without letting it change. Paired instances are
 * offered only while peering is on, public only while the instance allows
 * it; a recipe that has one of them already keeps the option and says that
 * it reads as instance meanwhile.
 *
 * Inside "chosen people", paired instances are share targets too, while
 * there are any to pick. A recipe that is a copy of a recipe from another
 * instance (`capped`) stays on this cookbook: it offers neither public nor
 * paired instances, and says why.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { listGroups, type PeerRef, type RecipeVisibility } from '@/features/recipes/api/recipes'
import UserPicker from '@/shared/cookbook/UserPicker.vue'

const visibility = defineModel<RecipeVisibility>('visibility', { required: true })
const sharedUserIds = defineModel<string[]>('sharedUserIds', { required: true })
const sharedGroupIds = defineModel<string[]>('sharedGroupIds', { required: true })
const sharedPeerIds = defineModel<string[]>('sharedPeerIds', { default: () => [] })
const props = withDefaults(
  defineProps<{
    locked?: boolean
    publicAllowed?: boolean
    /** Whether peering is on, so "paired instances" is offered. */
    peering?: boolean
    /** The paired instances the user may pick, plus those already chosen. */
    peerTargets?: PeerRef[]
    /** A copy of a mirror: never public, never to another instance. */
    capped?: boolean
    /** Names of the sub-recipes that do not go to every chosen instance. */
    peerHiddenNames?: string
  }>(),
  {
    locked: false,
    publicAllowed: false,
    peering: false,
    peerTargets: () => [],
    capped: false,
    peerHiddenNames: '',
  },
)

const { t } = useI18n()

const LEVELS = [
  { value: 'private', icon: 'mdi-lock-outline' },
  { value: 'household', icon: 'mdi-home-heart' },
  { value: 'shared', icon: 'mdi-account-multiple-outline' },
  { value: 'instance', icon: 'mdi-account-group-outline' },
  { value: 'peers', icon: 'mdi-transit-connection-variant' },
  { value: 'public', icon: 'mdi-earth' },
] as const

// Once the recipe was public or went to paired instances (loaded so), the
// option stays so it can be picked again after trying another level.
const seenPublic = ref(visibility.value === 'public')
const seenPeers = ref(visibility.value === 'peers')
watch(visibility, (value) => {
  if (value === 'public') seenPublic.value = true
  if (value === 'peers') seenPeers.value = true
})
const levels = computed(() =>
  LEVELS.filter((l) => {
    if (l.value === 'public') return !props.capped && (props.publicAllowed || seenPublic.value)
    if (l.value === 'peers') return !props.capped && (props.peering || seenPeers.value)
    return true
  }),
)
const peerOptions = computed(() => (props.capped ? [] : props.peerTargets))
const publicLimited = computed(() => visibility.value === 'public' && !props.publicAllowed)
const peersLimited = computed(() => visibility.value === 'peers' && !props.peering)

// Only people who manage groups can list them, so the group picker appears
// for them alone; everybody can share with chosen people.
const groups = ref<{ id: string; name: string }[] | null>(null)
const groupOptions = computed(() => groups.value ?? [])

onMounted(async () => {
  try {
    groups.value = (await listGroups()).map((g) => ({ id: g.id, name: g.name }))
  } catch {
    groups.value = null
  }
})
</script>

<template>
  <fieldset class="visibility" :disabled="locked">
    <legend class="field-label">{{ t('recipes.visibility.label') }}</legend>
    <div class="visibility-options">
      <label
        v-for="level in levels"
        :key="level.value"
        class="visibility-option"
        :class="{ 'visibility-option--on': visibility === level.value }"
      >
        <RadioButton
          v-model="visibility"
          :input-id="`visibility-${level.value}`"
          name="visibility"
          :value="level.value"
          :disabled="locked"
        />
        <span class="mdi" :class="level.icon" aria-hidden="true" />
        <span class="visibility-text">
          <span class="visibility-name">{{ t(`recipes.visibility.${level.value}`) }}</span>
          <small>{{ t(`recipes.visibility.${level.value}Hint`) }}</small>
        </span>
      </label>
    </div>
    <small v-if="publicLimited" class="field-hint" data-testid="public-limited">
      <span class="mdi mdi-information-outline" aria-hidden="true" />
      {{ t('recipes.visibility.publicLimited') }}
    </small>
    <small v-if="peersLimited" class="field-hint" data-testid="peers-limited">
      <span class="mdi mdi-information-outline" aria-hidden="true" />
      {{ t('recipes.visibility.peersLimited') }}
    </small>
    <small v-if="locked" class="field-hint">
      <span class="mdi mdi-lock-outline" aria-hidden="true" />
      {{ t('recipes.visibility.locked') }}
    </small>
    <small v-else class="field-hint">{{ t('recipes.visibility.draftHint') }}</small>
    <small v-if="capped" class="field-hint" data-testid="visibility-capped">
      <span class="mdi mdi-transit-connection-variant" aria-hidden="true" />
      {{ t('recipes.visibility.capped') }}
    </small>

    <div v-if="visibility === 'shared'" class="visibility-shares">
      <div class="field">
        <span id="share-users-label" class="field-label">{{ t('recipes.visibility.people') }}</span>
        <UserPicker
          v-model="sharedUserIds"
          input-id="share-users"
          labelledby="share-users-label"
          :disabled="locked"
        />
      </div>
      <div v-if="groups" class="field">
        <span id="share-groups-label" class="field-label">{{ t('recipes.visibility.groups') }}</span>
        <MultiSelect
          v-model="sharedGroupIds"
          :options="groupOptions"
          option-label="name"
          option-value="id"
          display="chip"
          filter
          fluid
          :disabled="locked"
          aria-labelledby="share-groups-label"
        />
      </div>
      <div v-if="peerOptions.length" class="field" data-testid="share-peers">
        <span id="share-peers-label" class="field-label">{{ t('recipes.visibility.instances') }}</span>
        <MultiSelect
          v-model="sharedPeerIds"
          :options="peerOptions"
          option-label="name"
          option-value="id"
          display="chip"
          fluid
          :disabled="locked"
          aria-labelledby="share-peers-label"
        />
        <small class="field-hint">{{ t('recipes.visibility.instancesHint') }}</small>
        <Message
          v-if="sharedPeerIds.length && peerHiddenNames"
          severity="warn"
          size="small"
          data-testid="peer-hidden-sub-recipes"
        >
          {{ t('recipes.visibility.peerHiddenSubRecipes', { names: peerHiddenNames }) }}
        </Message>
      </div>
    </div>
  </fieldset>
</template>

<style scoped lang="scss">
.visibility {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
  margin: 0;
  padding: 0;
  border: none;
}

.visibility-options {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-2);
}

.visibility-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 3.25rem;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  cursor: pointer;

  > .mdi {
    color: var(--p-text-muted-color);
    font-size: var(--font-size-xl);
  }
}

.visibility-option--on {
  border-color: var(--p-primary-color);
  background: var(--p-highlight-background);
}

.visibility:disabled .visibility-option {
  cursor: default;
  opacity: 0.7;
}

.visibility-text {
  display: flex;
  flex-direction: column;

  small {
    color: var(--p-text-muted-color);
  }
}

.visibility-name {
  font-weight: 700;
}

.visibility-shares {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-top: var(--space-2);
}

@media (min-width: $bp-sm) {
  .visibility-options {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
