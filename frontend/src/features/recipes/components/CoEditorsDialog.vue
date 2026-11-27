<script setup lang="ts">
/**
 * The owner picks the recipe's co-editors. Only people who can read the
 * recipe are offered, household members first and as one-tap suggestions.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import {
  getMyHousehold,
  getRecipeForEdit,
  listPeople,
  setCoEditors,
  type PersonRef,
} from '@/features/recipes/api/recipes'
import { coEditorCandidates, coEditorSuggestions } from '@/features/recipes/utils/coEditors'
import UserPicker from '@/shared/cookbook/UserPicker.vue'

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{ recipeId: string }>()
const emit = defineEmits<{ saved: [coEditors: PersonRef[]] }>()

const { t } = useI18n()
const toast = useAppToast()

const loading = ref(false)
const saving = ref(false)
const chosen = ref<string[]>([])
const candidates = ref<PersonRef[]>([])
const household = ref<PersonRef[]>([])
const isDraft = ref(false)

const current = ref<PersonRef[]>([])
// Someone already chosen stays listed even if they could no longer be picked.
const options = computed(() => {
  const known = new Set(candidates.value.map((p) => p.id))
  return [...candidates.value, ...current.value.filter((p) => !known.has(p.id))]
})
const suggestions = computed(() => coEditorSuggestions(candidates.value, household.value, chosen.value))

async function load() {
  loading.value = true
  try {
    const [recipe, people, mine] = await Promise.all([
      getRecipeForEdit(props.recipeId),
      listPeople().catch(() => []),
      getMyHousehold().catch(() => ({ household: null })),
    ])
    household.value = mine.household?.members ?? []
    current.value = recipe.co_editors
    chosen.value = recipe.co_editors.map((p) => p.id)
    isDraft.value = recipe.status === 'draft'
    candidates.value = coEditorCandidates({
      visibility: recipe.visibility,
      ownerId: recipe.owner?.id ?? null,
      everyone: people.map((p) => ({ id: p.id, display_name: p.display_name, avatar_id: p.avatar_id })),
      household: household.value,
      sharedUserIds: recipe.shared_user_ids,
    })
  } catch (err) {
    toast.error(err)
    visible.value = false
  } finally {
    loading.value = false
  }
}

watch(visible, (open) => {
  if (open) void load()
})

async function save() {
  saving.value = true
  try {
    const saved = await setCoEditors(props.recipeId, chosen.value)
    toast.success(t('recipes.coEditors.saved'))
    emit('saved', saved)
    visible.value = false
  } catch (err) {
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
    :header="t('recipes.coEditors.title')"
    :style="{ width: 'var(--dialog-width-sm)' }"
  >
    <form class="co-editors" @submit.prevent="save">
      <p class="hint">{{ t('recipes.coEditors.hint') }}</p>
      <div
        v-if="loading"
        class="co-editors-skeleton"
        role="status"
        :aria-label="t('recipes.loading')"
        data-testid="co-editors-skeleton"
      >
        <Skeleton width="40%" height="0.875rem" />
        <Skeleton height="2.75rem" />
        <Skeleton width="70%" height="0.75rem" />
      </div>
      <template v-else>
        <Message v-if="isDraft" severity="info">{{ t('recipes.coEditors.draftHint') }}</Message>
        <p v-if="!options.length" class="hint">{{ t('recipes.coEditors.noneAvailable') }}</p>
        <template v-else>
          <div v-if="suggestions.length" class="co-editors-suggested">
            <span class="field-label">{{ t('recipes.coEditors.suggested') }}</span>
            <div class="co-editors-chips">
              <Button
                v-for="person in suggestions"
                :key="person.id"
                :label="person.display_name"
                :aria-label="t('recipes.coEditors.add', { name: person.display_name })"
                icon="mdi mdi-plus"
                size="small"
                severity="secondary"
                outlined
                rounded
                @click="chosen = [...chosen, person.id]"
              />
            </div>
          </div>
          <div class="field">
            <span id="co-editors-label" class="field-label">{{ t('recipes.coEditors.people') }}</span>
            <UserPicker v-model="chosen" input-id="co-editors" labelledby="co-editors-label" :people="options" />
            <small class="field-hint">{{ t('recipes.coEditors.onlyReaders') }}</small>
          </div>
        </template>
      </template>
      <div class="row-actions">
        <Button :label="t('common.cancel')" text severity="secondary" @click="visible = false" />
        <Button type="submit" :label="t('common.save')" :loading="saving" :disabled="loading" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.co-editors {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.co-editors-skeleton {
  display: grid;
  gap: var(--space-2);
}

.co-editors-suggested {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.co-editors-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
