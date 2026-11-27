<script setup lang="ts">
/**
 * Accepting a recipe a paired instance shares with this one: what it is and
 * who wrote it, the sub-recipes it uses, and every catalogue entry this
 * instance has no mapping for yet, each with a decision that starts at the
 * suggestion. Every decision is saved for later recipes of that peer. A held
 * update of an existing mirror lists only its new entries; the mirror keeps
 * its previous version until it is accepted. Entries the backend still finds
 * undecided are marked.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import MappingDecisionFields from '@/features/admin-settings/components/MappingDecisionFields.vue'
import { incomingApi, type IncomingRecipe } from '@/features/admin-settings/api/peering'
import {
  decisionRequests,
  entryKey,
  incompleteKeys,
  initialDecision,
  missingKeysOf,
  type DecisionState,
} from '@/features/admin-settings/incomingRecipes'
import { useAppToast } from '@/core/composables/useAppToast'
import { errorCode } from '@/core/utils/errors'
import { formatDateTime } from '@/core/utils/dates'
import type { EquipmentResponse } from '@/shared/cookbook/types'

const props = withDefaults(defineProps<{ item: IncomingRecipe | null; equipment?: EquipmentResponse[] }>(), {
  equipment: () => [],
})
const emit = defineEmits<{ accepted: [item: IncomingRecipe, mirror: { id: string; title: string }]; close: [] }>()

const { t, te } = useI18n()
const toast = useAppToast()

const decisions = ref<Record<string, DecisionState>>({})
const missing = ref<string[]>([])
const saving = ref(false)
const visible = computed({
  get: () => props.item !== null,
  set: (open: boolean) => {
    if (!open) emit('close')
  },
})
const KIND_ORDER = ['ingredient', 'equipment', 'unit', 'tag'] as const
const groups = computed(() =>
  KIND_ORDER.map((kind) => ({ kind, entries: (props.item?.entries ?? []).filter((e) => e.kind === kind) })).filter(
    (g) => g.entries.length,
  ),
)

watch(
  () => props.item,
  (item) => {
    missing.value = []
    decisions.value = Object.fromEntries((item?.entries ?? []).map((e) => [entryKey(e), initialDecision(e)]))
  },
  { immediate: true },
)

// An allergen this release does not know keeps the peer's word for it.
const allergenLabel = (value: string) => (te(`allergens.${value}`) ? t(`allergens.${value}`) : value)

async function accept() {
  const item = props.item
  if (!item) return
  missing.value = incompleteKeys(item.entries, decisions.value)
  if (missing.value.length) {
    toast.error(null, 'adminArea.incoming.incomplete')
    return
  }
  saving.value = true
  try {
    const mirror = await incomingApi.accept(item.id, decisionRequests(item.entries, decisions.value))
    toast.success(t('adminArea.incoming.accepted', { title: mirror.title }))
    emit('accepted', item, mirror)
  } catch (err) {
    if (errorCode(err) === 'PeerMappingError') missing.value = missingKeysOf(err)
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('adminArea.incoming.reviewTitle', { title: item?.title ?? '' })"
    class="incoming-dialog"
  >
    <div v-if="item" class="incoming-body">
      <p class="hint">
        {{
          item.author_name
            ? t('adminArea.incoming.fromBy', { instance: item.peer.name, name: item.author_name })
            : t('adminArea.incoming.from', { instance: item.peer.name })
        }}
        · {{ formatDateTime(item.received_at) }}
      </p>
      <Message v-if="item.kind === 'update'" severity="info" data-testid="incoming-held-update">
        {{ t('adminArea.incoming.heldUpdate') }}
        <RouterLink v-if="item.mirror_id" :to="{ name: 'recipe', params: { id: item.mirror_id } }">
          {{ t('adminArea.incoming.openMirror') }}
        </RouterLink>
      </Message>
      <Message v-if="item.status === 'rejected'" severity="warn">{{ t('adminArea.incoming.acceptRejected') }}</Message>
      <p v-if="item.description" class="incoming-description">{{ item.description }}</p>

      <section v-if="item.sub_recipes.length" class="incoming-group">
        <h3 class="incoming-heading">{{ t('adminArea.incoming.subRecipes') }}</h3>
        <ul class="incoming-subs">
          <li v-for="sub in item.sub_recipes" :key="sub.source_id">
            <span>{{ sub.title ?? t('adminArea.incoming.subRecipeHidden') }}</span>
            <small class="text-muted">
              {{
                sub.mirrored
                  ? t('adminArea.incoming.subMirrored')
                  : sub.waiting
                    ? t('adminArea.incoming.subWaiting')
                    : t('adminArea.incoming.subMissing')
              }}
            </small>
          </li>
        </ul>
      </section>

      <p v-if="!item.entries.length" class="hint" data-testid="incoming-no-entries">
        {{ t('adminArea.incoming.nothingToDecide') }}
      </p>
      <p v-else class="hint">{{ t('adminArea.incoming.decideHint') }}</p>

      <section v-for="group in groups" :key="group.kind" class="incoming-group">
        <h3 class="incoming-heading">{{ t(`adminArea.incoming.kinds.${group.kind}`) }}</h3>
        <ul class="incoming-entries">
          <li
            v-for="entry in group.entries"
            :key="entryKey(entry)"
            class="incoming-entry"
            :data-testid="`entry-${entryKey(entry)}`"
            :data-missing="missing.includes(entryKey(entry)) ? 'true' : undefined"
          >
            <div class="incoming-entry-text">
              <strong>{{ entry.name }}</strong>
              <small v-if="Object.keys(entry.names).length > 1" class="text-muted">
                {{ Object.values(entry.names).join(' · ') }}
              </small>
              <small v-if="entry.allergens.length" class="text-muted">
                {{ t('adminArea.incoming.allergens', { names: entry.allergens.map(allergenLabel).join(', ') }) }}
              </small>
              <small v-if="entry.diet_markers.length" class="text-muted">
                {{ t('adminArea.incoming.markers', { names: entry.diet_markers.join(', ') }) }}
              </small>
              <small v-if="entry.suggestion" class="text-muted">
                {{ t('adminArea.incoming.suggestion', { name: entry.suggestion.name }) }}
              </small>
              <small v-if="missing.includes(entryKey(entry))" class="incoming-missing">
                {{ t('adminArea.incoming.missing') }}
              </small>
            </div>
            <MappingDecisionFields
              v-if="decisions[entryKey(entry)]"
              v-model="decisions[entryKey(entry)]!"
              :kind="entry.kind"
              :id-base="`incoming-${entry.kind}-${entry.source_id}`"
              :equipment="equipment"
              :invalid="missing.includes(entryKey(entry))"
            />
          </li>
        </ul>
      </section>

      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text @click="emit('close')" />
        <Button
          type="button"
          :label="t('adminArea.incoming.accept')"
          icon="mdi mdi-check"
          :loading="saving"
          data-testid="incoming-accept"
          @click="accept"
        />
      </div>
    </div>
  </Dialog>
</template>

<style scoped lang="scss">
.incoming-dialog {
  width: min(var(--dialog-width-lg), 100vw - 2 * var(--space-4));
}

.incoming-body {
  display: grid;
  gap: var(--space-3);
}

.incoming-description {
  margin: 0;
}

.incoming-group {
  display: grid;
  gap: var(--space-2);
}

.incoming-heading {
  margin: 0;
  font-size: var(--font-size-md);
}

.incoming-subs,
.incoming-entries {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.incoming-subs li {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}

.incoming-entry {
  display: grid;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--p-content-border-color);
}

.incoming-entry-text {
  display: grid;
  min-width: 0;
}

.incoming-missing {
  color: var(--p-red-500);
  font-weight: 700;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

@media (min-width: $bp-sm) {
  .incoming-entry {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
    align-items: start;
  }
}
</style>
